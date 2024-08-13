import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import date
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

# Initialize the Flask application
app = Flask(__name__)

# Enable CORS to allow requests from any domain
CORS(app)

# Set up the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///example.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Logger configuration
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')

# Get the current year and month
current_year = date.today().strftime('%Y')
current_month = date.today().strftime('%m')

# Create directories for the current year and month
year_month_dir = os.path.join(logs_dir, current_year, current_month)
os.makedirs(year_month_dir, exist_ok=True)

# Define the log file name using today's date
log_file = os.path.join(year_month_dir, f'{date.today()}.log')

# Create a RotatingFileHandler with log file rotation settings
log_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024, backupCount=5)
log_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(module)s:%(lineno)d] %(message)s'))

# Create a logger and set its level to INFO
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add the RotatingFileHandler to the logger
logger.addHandler(log_handler)

# Define the model for our database
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    description = db.Column(db.String(120), nullable=True)

    def __repr__(self):
        return f"Item('{self.name}', '{self.description}')"

# Initialize the database
with app.app_context():
    db.create_all()

# CRUD Operations

# Create a new item (preventing duplicates)
@app.route('/items', methods=['POST'])
def create_item():
    data = request.json
    existing_item = Item.query.filter_by(name=data['name']).first()
    if existing_item:
        logger.warning(f"Attempted to create a duplicate item: {data['name']}")
        return jsonify({"message": "Item with this name already exists"}), 400
    
    new_item = Item(name=data['name'], description=data.get('description'))
    db.session.add(new_item)
    db.session.commit()
    logger.info(f"Created new item: {new_item}")
    return jsonify({"message": "Item created", "item": {"id": new_item.id, "name": new_item.name, "description": new_item.description}}), 201

# Read all items (handle no records)
@app.route('/items', methods=['GET'])
def get_items():
    items = Item.query.all()
    if not items:
        logger.info("No records found when fetching all items")
        return jsonify({"message": "No records found"}), 200
    logger.info("Fetched all items")
    return jsonify([{"id": item.id, "name": item.name, "description": item.description} for item in items]), 200

# Read a single item by id (handle item not found)
@app.route('/items/<int:id>', methods=['GET'])
def get_item(id):
    item = Item.query.get(id)
    if item is None:
        logger.warning(f"Item with id {id} not found")
        return jsonify({"message": "Item not found"}), 404
    logger.info(f"Fetched item with id {id}: {item}")
    return jsonify({"id": item.id, "name": item.name, "description": item.description}), 200

# Update an item by id (handle item not found)
@app.route('/items/<int:id>', methods=['PUT'])
def update_item(id):
    item = Item.query.get(id)
    if item is None:
        logger.warning(f"Attempted to update non-existent item with id {id}")
        return jsonify({"message": "Item not found"}), 404
    
    data = request.json
    if 'name' in data:
        existing_item = Item.query.filter_by(name=data['name']).first()
        if existing_item and existing_item.id != id:
            logger.warning(f"Attempted to rename item to an existing name: {data['name']}")
            return jsonify({"message": "Item with this name already exists"}), 400
        item.name = data['name']
    
    item.description = data.get('description')
    db.session.commit()
    logger.info(f"Updated item with id {id}: {item}")
    return jsonify({"message": "Item updated", "item": {"id": item.id, "name": item.name, "description": item.description}}), 200

# Delete an item by id (handle item not found and item already deleted)
@app.route('/items/<int:id>', methods=['DELETE'])
def delete_item(id):
    item = Item.query.get(id)
    if item is None:
        logger.warning(f"Attempted to delete non-existent or already deleted item with id {id}")
        return jsonify({"message": "Item not found or already deleted"}), 404
    
    logger.info(f"Deleted item with id {id}: {item}")
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Item deleted"}), 200

# Run the application
if __name__ == '__main__':
    app.run(debug=True)
