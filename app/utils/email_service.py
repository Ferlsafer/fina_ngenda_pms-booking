"""
Email Service for Ngenda Hotel PMS
Handles password reset, notifications, and other system emails.
"""
from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from app import mail
from datetime import datetime


def _send_async(app, msg):
    """Send a mail message in a background thread."""
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            app.logger.error(f"Async email send failed: {str(e)}")


def send_password_reset_email(user, reset_token):
    """
    Send password reset email to user.

    Args:
        user: User object
        reset_token: Secure reset token
    """
    try:
        reset_url = f"{current_app.config.get('SERVER_NAME', 'http://localhost:5000')}/hms/reset-password/{reset_token}"

        msg = Message(
            subject='Password Reset Request - Ngenda Hotel PMS',
            recipients=[user.email],
            sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
            html=render_template(
                'hms/emails/password_reset.html',
                user=user,
                reset_url=reset_url,
                expiry_hours=current_app.config.get('MAIL_RESET_TOKEN_EXPIRY', 3600) // 3600
            )
        )

        app = current_app._get_current_object()
        Thread(target=_send_async, args=(app, msg), daemon=True).start()
        current_app.logger.info(f"Password reset email queued for {user.email}")
        return True

    except Exception as e:
        current_app.logger.error(f"Failed to queue password reset email to {user.email}: {str(e)}")
        return False


def send_welcome_email(user, temporary_password=None):
    """
    Send welcome email to new user.

    Args:
        user: User object
        temporary_password: Optional temporary password
    """
    try:
        login_url = f"{current_app.config.get('SERVER_NAME', 'http://localhost:5000')}/hms/login"

        msg = Message(
            subject='Welcome to Ngenda Hotel PMS',
            recipients=[user.email],
            sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
            html=render_template(
                'hms/emails/welcome.html',
                user=user,
                login_url=login_url,
                temporary_password=temporary_password
            )
        )

        app = current_app._get_current_object()
        Thread(target=_send_async, args=(app, msg), daemon=True).start()
        current_app.logger.info(f"Welcome email queued for {user.email}")
        return True

    except Exception as e:
        current_app.logger.error(f"Failed to queue welcome email to {user.email}: {str(e)}")
        return False


def send_booking_notification_to_hotel(booking, room_type, nights):
    """
    Email the hotel inbox when a new booking arrives from the website.

    Args:
        booking: Booking object
        room_type: RoomType object
        nights: int — number of nights
    """
    try:
        hotel_email = current_app.config.get('MAIL_HOTEL_EMAIL', 'hotels@ngendagroup.africa')
        sender = current_app.config.get('MAIL_DEFAULT_SENDER')

        subject = f'[New Booking] {booking.booking_reference} — {booking.guest_name}'

        body = (
            f"A new booking has been made through the website.\n\n"
            f"Reference  : {booking.booking_reference}\n"
            f"Guest      : {booking.guest_name}\n"
            f"Phone      : {booking.guest_phone}\n"
            f"Email      : {booking.guest_email}\n"
            f"Room       : {room_type.name}\n"
            f"Check-in   : {booking.check_in_date.strftime('%A, %d %B %Y')}\n"
            f"Check-out  : {booking.check_out_date.strftime('%A, %d %B %Y')}\n"
            f"Nights     : {nights}\n"
            f"Total      : TZS {booking.total_amount:,.0f}\n"
            f"Adults     : {booking.adults}   Children: {booking.children}\n"
        )
        if booking.special_requests:
            body += f"Special Requests: {booking.special_requests}\n"

        msg = Message(
            subject=subject,
            recipients=[hotel_email],
            sender=sender,
            body=body,
        )

        app = current_app._get_current_object()
        Thread(target=_send_async, args=(app, msg), daemon=True).start()
        current_app.logger.info(
            f"Booking notification queued to {hotel_email} for {booking.booking_reference}"
        )
        return True

    except Exception as e:
        current_app.logger.error(f"Failed to queue booking notification email: {str(e)}")
        return False


def send_contact_message_to_hotel(sender_name, sender_email, message_body):
    """
    Forward a website contact form submission to the hotel inbox.

    Args:
        sender_name: str
        sender_email: str
        message_body: str
    """
    try:
        hotel_email = current_app.config.get('MAIL_HOTEL_EMAIL', 'hotels@ngendagroup.africa')
        sender = current_app.config.get('MAIL_DEFAULT_SENDER')

        msg = Message(
            subject=f'[Website Contact] Message from {sender_name}',
            recipients=[hotel_email],
            reply_to=sender_email,
            sender=sender,
            body=(
                f"New message received from the website contact form.\n\n"
                f"Name   : {sender_name}\n"
                f"Email  : {sender_email}\n"
                f"Message:\n{message_body}\n\n"
                f"Reply directly to this email to respond to the guest."
            ),
        )

        app = current_app._get_current_object()
        Thread(target=_send_async, args=(app, msg), daemon=True).start()
        current_app.logger.info(
            f"Contact form message from {sender_email} queued to {hotel_email}"
        )
        return True

    except Exception as e:
        current_app.logger.error(f"Failed to queue contact notification email: {str(e)}")
        return False


def send_user_invitation_email(user, invited_by, temporary_password):
    """
    Send user invitation email.

    Args:
        user: User object
        invited_by: User who created the account
        temporary_password: Temporary password for first login
    """
    try:
        login_url = f"{current_app.config.get('SERVER_NAME', 'http://localhost:5000')}/hms/login"

        msg = Message(
            subject='You have been invited to Ngenda Hotel PMS',
            recipients=[user.email],
            sender=current_app.config.get('MAIL_DEFAULT_SENDER'),
            html=render_template(
                'hms/emails/invitation.html',
                user=user,
                invited_by=invited_by,
                login_url=login_url,
                temporary_password=temporary_password
            )
        )

        app = current_app._get_current_object()
        Thread(target=_send_async, args=(app, msg), daemon=True).start()
        current_app.logger.info(f"Invitation email queued for {user.email}")
        return True

    except Exception as e:
        current_app.logger.error(f"Failed to queue invitation email to {user.email}: {str(e)}")
        return False
