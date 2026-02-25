import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.hotel import Hotel
from app.models.owner import Owner

app = create_app()

with app.app_context():
    # Create or update Ngenda Hotel
    hotel = Hotel.query.filter_by(name='Ngenda Hotel & Apartments').first()
    
    if not hotel:
        # Create owner if not exists
        owner = Owner.query.filter_by(email='info@ngendahotel.com').first()
        if not owner:
            owner = Owner(
                name='Ngenda Hotel Group',
                email='info@ngendahotel.com',
                phone='+255671271247'
            )
            db.session.add(owner)
            db.session.flush()
        
        hotel = Hotel(
            owner_id=owner.id,
            name='Ngenda Hotel & Apartments',
            display_name='Ngenda Hotel',
            address='Isyesye–Hayanga',
            city='Mbeya',
            country='Tanzania',
            phone='+255671271247',
            email='info@ngendahotel.com',
            website_url='https://hotel.ngendagroup.africa',
            check_in_time='14:00',
            check_out_time='11:00',
            currency='TZS',
            timezone='Africa/Dar_es_Salaam',
            # Branding
            email_header_color='#2c3e50',
            email_footer_text='Thank you for choosing Ngenda Hotel. We look forward to welcoming you!',
            # Policies
            cancellation_policy='Cancellations must be made at least 24 hours before check-in to avoid charges.',
            children_policy='Children under 12 stay free when sharing with adults.',
            pet_policy='Pets are not allowed except for service animals.',
            payment_policy='Full payment required at check-in. We accept cash, mobile money, and credit cards.'
        )
        db.session.add(hotel)
        db.session.commit()
        print("✅ Created Ngenda Hotel")
    else:
        # Update with website URL
        hotel.website_url = 'https://hotel.ngendagroup.africa'
        hotel.display_name = 'Ngenda Hotel'
        hotel.email_footer_text = 'Thank you for choosing Ngenda Hotel. We look forward to welcoming you!'
        db.session.commit()
        print("✅ Updated Ngenda Hotel")
