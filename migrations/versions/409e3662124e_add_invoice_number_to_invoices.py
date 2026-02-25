"""add_invoice_number_to_invoices

Revision ID: 409e3662124e
Revises: 30e730748865
Create Date: 2026-02-18 11:51:35.097679

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '409e3662124e'
down_revision = '30e730748865'
branch_labels = None
depends_on = None


def upgrade():
    # Add missing columns to invoices table
    with op.batch_alter_table("invoices", schema=None) as batch_op:
        batch_op.add_column(sa.Column("invoice_number", sa.String(50), nullable=True))
        batch_op.add_column(sa.Column("due_date", sa.Date(), nullable=True))
    
    # Generate invoice numbers for existing records
    op.execute("""
        UPDATE invoices 
        SET invoice_number = 'INV-' || LPAD(id::text, 6, '0')
        WHERE invoice_number IS NULL
    """)
    
    # Make invoice_number unique and not nullable
    batch_op.alter_column("invoice_number", nullable=False)
    batch_op.create_unique_constraint("uq_invoice_number", ["invoice_number"])


def downgrade():
    # Remove the added columns and constraint
    with op.batch_alter_table("invoices", schema=None) as batch_op:
        batch_op.drop_constraint("uq_invoice_number", type_="unique")
        batch_op.drop_column("invoice_number")
        batch_op.drop_column("due_date")
