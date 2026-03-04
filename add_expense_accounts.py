#!/usr/bin/env python3
"""
Add sample expense accounts to Chart of Accounts.
This ensures the expense breakdown in financial reports shows data.
"""
import os
from dotenv import load_dotenv
load_dotenv()

from app import create_app, db
from app.models import ChartOfAccount

def add_expense_accounts():
    app = create_app()
    with app.app_context():
        # Sample expense accounts to add
        expense_accounts = [
            ('Salaries & Wages', 'Expense'),
            ('Utilities', 'Expense'),
            ('Maintenance & Repairs', 'Expense'),
            ('Housekeeping Supplies', 'Expense'),
            ('Food & Beverage Cost', 'Expense'),
            ('Marketing & Advertising', 'Expense'),
            ('Insurance', 'Expense'),
            ('Property Taxes', 'Expense'),
            ('Depreciation', 'Expense'),
            ('Office Supplies', 'Expense'),
            ('Bank Charges', 'Expense'),
            ('Miscellaneous Expenses', 'Expense'),
        ]
        
        hotel_id = 1  # Default hotel
        
        print("Adding expense accounts...")
        added_count = 0
        
        for name, account_type in expense_accounts:
            # Check if account already exists
            existing = ChartOfAccount.query.filter_by(
                hotel_id=hotel_id,
                name=name
            ).first()
            
            if not existing:
                account = ChartOfAccount(
                    hotel_id=hotel_id,
                    name=name,
                    type=account_type
                )
                db.session.add(account)
                added_count += 1
                print(f"  ✓ Added: {name}")
            else:
                print(f"  - Exists: {name}")
        
        db.session.commit()
        print(f"\n✓ Added {added_count} expense accounts")
        
        # Show all accounts
        print("\n=== All Chart of Accounts ===")
        accounts = ChartOfAccount.query.filter_by(hotel_id=hotel_id).all()
        by_type = {}
        for acc in accounts:
            if acc.type not in by_type:
                by_type[acc.type] = []
            by_type[acc.type].append(acc.name)
        
        for acc_type, names in sorted(by_type.items()):
            print(f"\n{acc_type}:")
            for name in names:
                print(f"  - {name}")

if __name__ == '__main__':
    add_expense_accounts()
