from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.extensions import db
from app.core.access import get_allowed_hotel_ids, require_hotel_access, get_current_hotel_id
from app.restaurant.models import (
    MenuCategory, MenuItem, MenuItemInventory,
    RestaurantTable, RestaurantOrder, RestaurantOrderItem,
)
from app.models.inventory import InventoryItem
from decimal import Decimal
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import uuid

bp = Blueprint('restaurant', __name__)


# ============================================
# MENU MANAGEMENT ROUTES (Clean Page-Based)
# ============================================

@bp.route('/menu')
@login_required
def menu():
    """Main menu management page"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("dashboard.index"))

    categories = MenuCategory.query.filter_by(
        hotel_id=hotel_id,
        deleted_at=None
    ).order_by(MenuCategory.display_order, MenuCategory.name).all()

    items = MenuItem.query.filter_by(
        hotel_id=hotel_id,
        deleted_at=None
    ).all()

    # Calculate item counts
    for category in categories:
        category.item_count = MenuItem.query.filter_by(
            category_id=category.id,
            deleted_at=None
        ).count()

    return render_template('restaurant/menu.html',
                          categories=categories,
                          items=items)


# ============================================
# CATEGORY ROUTES
# ============================================

@bp.route('/category/create', methods=['GET', 'POST'])
@login_required
def category_create():
    """Create new category"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("dashboard.index"))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        display_order = request.form.get('display_order', 0, type=int)
        is_active = request.form.get('is_active') == 'on'

        if not name:
            flash("Category name is required.", "danger")
            return redirect(url_for('restaurant.category_create'))

        category = MenuCategory(
            hotel_id=hotel_id,
            name=name,
            description=description,
            display_order=display_order,
            is_active=is_active
        )
        db.session.add(category)
        db.session.commit()

        flash(f"Category '{name}' created successfully.", "success")
        return redirect(url_for('restaurant.menu'))

    return render_template('restaurant/category_form.html',
                          title='Add Category',
                          category=None)


@bp.route('/category/<int:category_id>/edit', methods=['GET', 'POST'])
@login_required
def category_edit(category_id):
    """Edit existing category"""
    category = MenuCategory.query.get_or_404(category_id)
    require_hotel_access(category.hotel_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        display_order = request.form.get('display_order', 0, type=int)
        is_active = request.form.get('is_active') == 'on'

        if not name:
            flash("Category name is required.", "danger")
            return redirect(url_for('restaurant.category_edit', category_id=category_id))

        category.name = name
        category.description = description
        category.display_order = display_order
        category.is_active = is_active
        db.session.commit()

        flash(f"Category '{name}' updated successfully.", "success")
        return redirect(url_for('restaurant.menu'))

    return render_template('restaurant/category_form.html',
                          title='Edit Category',
                          category=category)


@bp.route('/category/<int:category_id>/delete', methods=['POST'])
@login_required
def category_delete(category_id):
    """Delete category (soft delete)"""
    category = MenuCategory.query.get_or_404(category_id)
    require_hotel_access(category.hotel_id)

    # Uncategorize items in this category
    MenuItem.query.filter_by(category_id=category_id).update({'category_id': None})

    category.deleted_at = datetime.utcnow()
    db.session.commit()

    flash("Category deleted successfully.", "success")
    return redirect(url_for('restaurant.menu'))


# ============================================
# MENU ITEM ROUTES
# ============================================

@bp.route('/item/create', methods=['GET', 'POST'])
@login_required
def item_create():
    """Create new menu item"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("dashboard.index"))

    categories = MenuCategory.query.filter_by(
        hotel_id=hotel_id,
        deleted_at=None
    ).all()

    inventory_items = InventoryItem.query.filter_by(
        hotel_id=hotel_id,
        deleted_at=None
    ).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category_id = request.form.get('category_id', type=int) or None
        price = request.form.get('price', type=float)
        cost = request.form.get('cost', type=float) or None
        tax_rate = request.form.get('tax_rate', 0, type=float)
        preparation_time = request.form.get('preparation_time', type=int) or None
        is_available = request.form.get('is_available') == 'on'

        if not name:
            flash("Item name is required.", "danger")
            return redirect(url_for('restaurant.item_create'))

        if not price:
            flash("Price is required.", "danger")
            return redirect(url_for('restaurant.item_create'))

        # Handle image upload
        image_url = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
                if ext not in current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif'}):
                    ext = 'jpg'
                new_filename = f"{uuid.uuid4().hex}.{ext}"

                upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'menu')
                os.makedirs(upload_dir, exist_ok=True)
                file.save(os.path.join(upload_dir, new_filename))
                image_url = url_for('static', filename=f'uploads/menu/{new_filename}')

        item = MenuItem(
            hotel_id=hotel_id,
            category_id=category_id,
            name=name,
            description=description,
            price=price,
            cost=cost,
            tax_rate=tax_rate,
            preparation_time=preparation_time,
            is_available=is_available,
            image_url=image_url
        )
        db.session.add(item)
        db.session.flush()

        # Handle inventory links
        inventory_ids = request.form.getlist('inventory_item_id[]')
        quantities = request.form.getlist('quantity_needed[]')
        for inv_id, qty in zip(inventory_ids, quantities):
            if inv_id and qty:
                link = MenuItemInventory(
                    menu_item_id=item.id,
                    inventory_item_id=int(inv_id),
                    quantity_needed=float(qty)
                )
                db.session.add(link)

        db.session.commit()

        flash(f"Menu item '{name}' created successfully.", "success")
        return redirect(url_for('restaurant.menu'))

    return render_template('restaurant/item_form.html',
                          title='Add Menu Item',
                          item=None,
                          categories=categories,
                          inventory_items=inventory_items)


@bp.route('/item/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def item_edit(item_id):
    """Edit existing menu item"""
    item = MenuItem.query.get_or_404(item_id)
    require_hotel_access(item.hotel_id)

    hotel_id = item.hotel_id
    categories = MenuCategory.query.filter_by(
        hotel_id=hotel_id,
        deleted_at=None
    ).all()

    inventory_items = InventoryItem.query.filter_by(
        hotel_id=hotel_id,
        deleted_at=None
    ).all()

    if request.method == 'POST':
        item.name = request.form.get('name', '').strip()
        item.description = request.form.get('description', '').strip()
        item.category_id = request.form.get('category_id', type=int) or None
        item.price = request.form.get('price', type=float)
        item.cost = request.form.get('cost', type=float) or None
        item.tax_rate = request.form.get('tax_rate', 0, type=float)
        item.preparation_time = request.form.get('preparation_time', type=int) or None
        item.is_available = request.form.get('is_available') == 'on'

        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                filename = secure_filename(file.filename)
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
                if ext in current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif'}):
                    new_filename = f"{uuid.uuid4().hex}.{ext}"
                    upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'menu')
                    os.makedirs(upload_dir, exist_ok=True)
                    file.save(os.path.join(upload_dir, new_filename))
                    item.image_url = url_for('static', filename=f'uploads/menu/{new_filename}')

        # Handle remove image
        if request.form.get('remove_image'):
            item.image_url = None

        # Update inventory links
        MenuItemInventory.query.filter_by(menu_item_id=item.id).delete()
        inventory_ids = request.form.getlist('inventory_item_id[]')
        quantities = request.form.getlist('quantity_needed[]')
        for inv_id, qty in zip(inventory_ids, quantities):
            if inv_id and qty:
                link = MenuItemInventory(
                    menu_item_id=item.id,
                    inventory_item_id=int(inv_id),
                    quantity_needed=float(qty)
                )
                db.session.add(link)

        db.session.commit()

        flash(f"Menu item '{item.name}' updated successfully.", "success")
        return redirect(url_for('restaurant.menu'))

    return render_template('restaurant/item_form.html',
                          title='Edit Menu Item',
                          item=item,
                          categories=categories,
                          inventory_items=inventory_items)


@bp.route('/item/<int:item_id>/delete', methods=['POST'])
@login_required
def item_delete(item_id):
    """Delete menu item (soft delete)"""
    item = MenuItem.query.get_or_404(item_id)
    require_hotel_access(item.hotel_id)

    item.deleted_at = datetime.utcnow()
    db.session.commit()

    flash("Menu item deleted successfully.", "success")
    return redirect(url_for('restaurant.menu'))


# ============================================
# POS & KITCHEN ROUTES
# ============================================

@bp.route('/pos')
@login_required
def pos():
    """POS interface - tables grid and quick items"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("dashboard.index"))
    tables = RestaurantTable.query.filter_by(hotel_id=hotel_id).order_by(RestaurantTable.table_number).all()
    pos_items = MenuItem.query.filter(
        MenuItem.hotel_id == hotel_id,
        MenuItem.deleted_at.is_(None),
        MenuItem.is_available == True
    ).order_by(MenuItem.name).all()
    return render_template('restaurant/pos.html', tables=tables, pos_items=pos_items)


@bp.route('/pos/table/<int:table_id>')
@login_required
def pos_table_orders(table_id):
    """Get orders for a table (JSON for AJAX)"""
    table = RestaurantTable.query.get_or_404(table_id)
    if not require_hotel_access(table.hotel_id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    orders = RestaurantOrder.query.filter_by(table_id=table_id).filter(
        RestaurantOrder.status.in_(['pending', 'preparing', 'ready'])
    ).order_by(RestaurantOrder.created_at.desc()).all()
    return jsonify({
        'success': True,
        'orders': [{'id': o.id, 'status': o.status, 'total': float(o.total)} for o in orders]
    })


@bp.route('/pos/order/create', methods=['POST'])
@login_required
def pos_order_create():
    """Create new order (optionally for a table)"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        return jsonify({'success': False, 'error': 'No hotel selected'}), 400
    table_id = request.form.get('table_id') or (request.json and request.json.get('table_id'))
    table = None
    if table_id:
        table = RestaurantTable.query.get(int(table_id))
        if not table or table.hotel_id != hotel_id:
            return jsonify({'success': False, 'error': 'Invalid table'}), 400
        if table.status == 'available':
            table.status = 'occupied'
    order = RestaurantOrder(hotel_id=hotel_id, table_id=int(table_id) if table_id else None)
    db.session.add(order)
    db.session.commit()
    return jsonify({'success': True, 'order_id': order.id})


@bp.route('/pos/order/<int:order_id>/add-item', methods=['POST'])
@login_required
def pos_order_add_item(order_id):
    """Add item to order"""
    order = RestaurantOrder.query.get_or_404(order_id)
    if not require_hotel_access(order.hotel_id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    data = request.get_json(force=True, silent=True) or request.form
    menu_item_id = data.get('menu_item_id') or data.get('item_id')
    quantity = int(data.get('quantity', 1))
    if not menu_item_id:
        return jsonify({'success': False, 'error': 'menu_item_id required'}), 400
    item = MenuItem.query.get(int(menu_item_id))
    if not item or item.hotel_id != order.hotel_id:
        return jsonify({'success': False, 'error': 'Invalid item'}), 400
    unit_price = item.price
    line = RestaurantOrderItem(order_id=order_id, menu_item_id=item.id, quantity=quantity, unit_price=unit_price)
    db.session.add(line)
    db.session.flush()
    subtotal = sum(float(l.unit_price * l.quantity) for l in order.items)
    order.subtotal = Decimal(str(subtotal))
    default_tax = getattr(current_app.config, 'DEFAULT_TAX_RATE', 10) or 10
    order.tax = order.subtotal * Decimal(str(default_tax)) / 100
    order.total = order.subtotal + order.tax
    db.session.commit()
    return jsonify({'success': True, 'order_id': order_id, 'subtotal': float(order.subtotal), 'total': float(order.total)})


@bp.route('/pos/order/<int:order_id>/status', methods=['POST'])
@login_required
def pos_order_status(order_id):
    """Update order status"""
    order = RestaurantOrder.query.get_or_404(order_id)
    if not require_hotel_access(order.hotel_id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    data = request.get_json(force=True, silent=True) or request.form
    status = data.get('status')
    if status not in ('pending', 'preparing', 'ready', 'served', 'paid'):
        return jsonify({'success': False, 'error': 'Invalid status'}), 400
    order.status = status
    if status == 'paid':
        order.completed_at = datetime.utcnow()
        if order.table_id:
            t = RestaurantTable.query.get(order.table_id)
            if t:
                t.status = 'available'
    db.session.commit()
    return jsonify({'success': True, 'status': order.status})


@bp.route('/pos/order/<int:order_id>/split', methods=['POST'])
@login_required
def pos_order_split(order_id):
    """Split bill (placeholder - create multiple orders or split lines)"""
    order = RestaurantOrder.query.get_or_404(order_id)
    if not require_hotel_access(order.hotel_id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    ways = int(request.form.get('split_ways') or request.json.get('split_ways', 2))
    if ways < 2:
        return jsonify({'success': False, 'error': 'Split ways must be >= 2'}), 400
    # Simplified: just return success; full impl would create child orders
    return jsonify({'success': True, 'message': f'Bill split into {ways} ways (backend can create separate orders)'})


@bp.route('/pos/order/<int:order_id>/payment', methods=['POST'])
@login_required
def pos_order_payment(order_id):
    """Process payment (cash/card/room charge)"""
    order = RestaurantOrder.query.get_or_404(order_id)
    if not require_hotel_access(order.hotel_id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    method = request.form.get('method') or (request.json or {}).get('method', 'cash')
    order.status = 'paid'
    order.completed_at = datetime.utcnow()
    if order.table_id:
        t = RestaurantTable.query.get(order.table_id)
        if t:
            t.status = 'available'
    db.session.commit()
    return jsonify({'success': True, 'status': 'paid', 'method': method})


@bp.route('/kitchen')
@login_required
def kitchen():
    """Kitchen display - orders by status"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("dashboard.index"))
    pending = RestaurantOrder.query.filter_by(hotel_id=hotel_id, status='pending').order_by(RestaurantOrder.created_at).all()
    preparing = RestaurantOrder.query.filter_by(hotel_id=hotel_id, status='preparing').order_by(RestaurantOrder.created_at).all()
    ready = RestaurantOrder.query.filter_by(hotel_id=hotel_id, status='ready').order_by(RestaurantOrder.completed_at).all()
    return render_template('restaurant/kitchen.html', pending=pending, preparing=preparing, ready=ready)


@bp.route('/kitchen/order/<int:order_id>/status', methods=['POST'])
@login_required
def kitchen_order_status(order_id):
    """Update order status from kitchen"""
    order = RestaurantOrder.query.get_or_404(order_id)
    if not require_hotel_access(order.hotel_id):
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    data = request.get_json(force=True, silent=True) or request.form
    status = data.get('status')
    if status not in ('pending', 'preparing', 'ready', 'served'):
        return jsonify({'success': False, 'error': 'Invalid status'}), 400
    order.status = status
    db.session.commit()
    return jsonify({'success': True, 'status': order.status})


@bp.route('/tables/layout/save', methods=['POST'])
@login_required
def tables_layout_save():
    """Save table positions from drag-drop"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        return jsonify({'success': False, 'error': 'No hotel selected'}), 400
    data = request.get_json(force=True, silent=True)
    positions = data.get('positions') if data else []
    for p in positions:
        t = RestaurantTable.query.filter_by(id=p.get('id'), hotel_id=hotel_id).first()
        if t:
            t.position_x = int(p.get('x', 0))
            t.position_y = int(p.get('y', 0))
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    """Order detail page"""
    order = RestaurantOrder.query.get_or_404(order_id)
    if not require_hotel_access(order.hotel_id):
        flash("Access denied.", "danger")
        return redirect(url_for("restaurant.pos"))
    return render_template('restaurant/order_detail.html', order=order)


@bp.route('/order/<int:order_id>/cancel', methods=['POST'])
@login_required
def cancel_order(order_id):
    """Cancel an order"""
    order = RestaurantOrder.query.get_or_404(order_id)
    if not require_hotel_access(order.hotel_id):
        flash("Access denied.", "danger")
        return redirect(url_for("restaurant.pos"))
    if order.status == 'paid':
        flash("Cannot cancel a paid order.", "warning")
        return redirect(url_for("restaurant.order_detail", order_id=order_id))
    order.status = 'cancelled'
    if order.table_id:
        t = RestaurantTable.query.get(order.table_id)
        if t:
            t.status = 'available'
    db.session.commit()
    flash("Order cancelled.", "info")
    return redirect(url_for("restaurant.pos"))


@bp.route('/tables/map')
@login_required
def table_map():
    """Table map - drag to arrange"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        flash("Please select a hotel first.", "warning")
        return redirect(url_for("dashboard.index"))
    tables = RestaurantTable.query.filter_by(hotel_id=hotel_id).all()
    map_tables = [{'id': t.id, 'number': t.table_number, 'status': t.status, 'x': t.position_x or 0, 'y': t.position_y or 0, 'w': 80, 'h': 80} for t in tables]
    if not map_tables:
        for i in range(1, 11):
            t = RestaurantTable(hotel_id=hotel_id, table_number=str(i), capacity=4, position_x=(i - 1) % 5 * 100, position_y=(i - 1) // 5 * 100)
            db.session.add(t)
        db.session.commit()
        tables = RestaurantTable.query.filter_by(hotel_id=hotel_id).all()
        map_tables = [{'id': t.id, 'number': t.table_number, 'status': t.status, 'x': t.position_x or 0, 'y': t.position_y or 0, 'w': 80, 'h': 80} for t in tables]
    return render_template('restaurant/table_map.html', map_tables=map_tables)


# ============================================
# HELPER ENDPOINTS (Keep for API usage)
# ============================================

@bp.route('/api/inventory-items')
@login_required
def api_get_inventory_items():
    """Get all inventory items for dropdowns"""
    hotel_id = get_current_hotel_id()
    if not hotel_id:
        return jsonify({'success': False, 'error': 'No hotel selected'}), 400

    items = InventoryItem.query.filter_by(
        hotel_id=hotel_id,
        deleted_at=None
    ).order_by(InventoryItem.name).all()

    result = [{
        'id': item.id,
        'name': f"{item.name} ({item.unit})",
        'unit': item.unit,
        'current_stock': float(item.current_stock)
    } for item in items]

    return jsonify({'success': True, 'items': result})
