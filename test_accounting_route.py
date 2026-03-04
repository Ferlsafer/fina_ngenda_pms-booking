#!/usr/bin/env python3
"""Test the accounting reports route directly"""
import os
from dotenv import load_dotenv
load_dotenv()

from app import create_app, db
from app.models import Invoice, Payment, JournalEntry, ChartOfAccount, Booking
from datetime import datetime, date, timedelta
from calendar import monthrange

app = create_app()

with app.app_context():
    try:
        hotel_id = 1
        period = 'this_month'
        today = date.today()
        
        # Calculate date range
        if period == 'this_month':
            start_date = today.replace(day=1)
            end_date = today.replace(day=monthrange(today.year, today.month)[1])
        else:
            start_date = today.replace(day=1)
            end_date = today
        
        print(f"Testing with hotel_id={hotel_id}, start={start_date}, end={end_date}")
        
        # Test 1: Invoice revenue
        print("\n1. Testing invoice revenue query...")
        total_invoice_revenue = db.session.query(db.func.coalesce(db.func.sum(Invoice.total), 0)).join(
            Booking
        ).filter(
            Invoice.hotel_id == hotel_id,
            Invoice.deleted_at.is_(None),
            Invoice.created_at >= datetime.combine(start_date, datetime.min.time()),
            Invoice.created_at <= datetime.combine(end_date, datetime.max.time())
        ).scalar()
        print(f"   Invoice revenue: {total_invoice_revenue}")
        
        # Test 2: Payment revenue
        print("\n2. Testing payment revenue query...")
        total_payment_revenue = db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0)).join(
            Booking
        ).filter(
            Payment.hotel_id == hotel_id,
            Payment.deleted_at.is_(None),
            Payment.status.in_(['completed', 'confirmed']),
            Payment.created_at >= datetime.combine(start_date, datetime.min.time()),
            Payment.created_at <= datetime.combine(end_date, datetime.max.time())
        ).scalar()
        print(f"   Payment revenue: {total_payment_revenue}")
        
        # Test 3: Payment methods
        print("\n3. Testing payment methods query...")
        payment_methods = db.session.query(
            Payment.payment_method,
            db.func.coalesce(db.func.sum(Payment.amount), 0)
        ).filter(
            Payment.hotel_id == hotel_id,
            Payment.deleted_at.is_(None),
            Payment.status.in_(['completed', 'confirmed']),
            Payment.created_at >= datetime.combine(start_date, datetime.min.time()),
            Payment.created_at <= datetime.combine(end_date, datetime.max.time())
        ).group_by(Payment.payment_method).all()
        print(f"   Payment methods: {payment_methods}")
        
        # Test 4: Expenses
        print("\n4. Testing expenses query...")
        total_expenses = db.session.query(db.func.coalesce(db.func.sum(JournalLine.debit), 0)).join(
            JournalEntry
        ).filter(
            JournalEntry.hotel_id == hotel_id,
            JournalEntry.date >= start_date,
            JournalEntry.date <= end_date,
            JournalEntry.deleted_at.is_(None)
        ).scalar()
        print(f"   Total expenses: {total_expenses}")
        
        # Test 5: Daily revenue
        print("\n5. Testing daily revenue query...")
        daily_revenue = db.session.query(
            db.func.date_trunc('day', Payment.created_at).label('payment_date'),
            db.func.coalesce(db.func.sum(Payment.amount), 0)
        ).filter(
            Payment.hotel_id == hotel_id,
            Payment.deleted_at.is_(None),
            Payment.status.in_(['completed', 'confirmed']),
            Payment.created_at >= datetime.combine(start_date, datetime.min.time()),
            Payment.created_at <= datetime.combine(end_date, datetime.max.time())
        ).group_by(db.func.date_trunc('day', Payment.created_at)).order_by(
            db.func.date_trunc('day', Payment.created_at)
        ).all()
        print(f"   Daily revenue rows: {len(daily_revenue)}")
        
        # Test 6: Outstanding receivables
        print("\n6. Testing outstanding receivables query...")
        outstanding_receivables = db.session.query(db.func.coalesce(db.func.sum(Invoice.total), 0)).filter(
            Invoice.hotel_id == hotel_id,
            Invoice.deleted_at.is_(None),
            Invoice.status.in_(['Unpaid', 'Partial'])
        ).scalar()
        print(f"   Outstanding: {outstanding_receivables}")
        
        # Test 7: Accounts payable
        print("\n7. Testing accounts payable query...")
        accounts_payable = db.session.query(db.func.coalesce(db.func.sum(JournalLine.credit), 0)).join(
            ChartOfAccount
        ).filter(
            ChartOfAccount.hotel_id == hotel_id,
            ChartOfAccount.account_type.in_(['liability', 'Liability']),
            JournalLine.deleted_at.is_(None)
        ).scalar()
        print(f"   Accounts payable: {accounts_payable}")
        
        print("\n✅ All queries executed successfully!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
