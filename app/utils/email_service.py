"""
Email Service for Ngenda Hotel PMS
Handles password reset, notifications, and other system emails.
"""
from flask import current_app, render_template
from flask_mail import Message
from app import mail
from datetime import datetime


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
        
        mail.send(msg)
        current_app.logger.info(f"Password reset email sent to {user.email}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
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
        
        mail.send(msg)
        current_app.logger.info(f"Welcome email sent to {user.email}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
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
        
        mail.send(msg)
        current_app.logger.info(f"Invitation email sent to {user.email}")
        return True
        
    except Exception as e:
        current_app.logger.error(f"Failed to send invitation email to {user.email}: {str(e)}")
        return False
