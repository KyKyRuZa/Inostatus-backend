
import logging
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import Request

DEV_MODE = os.getenv('DEV_MODE', 'true').lower() == 'true'

audit_logger = logging.getLogger('audit')
audit_logger.setLevel(logging.INFO)

audit_logger.handlers.clear()

if DEV_MODE:
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter('%(asctime)s [AUDIT] %(message)s'))
    audit_logger.addHandler(console_handler)
else:
    LOGS_DIR = os.getenv('LOGS_DIR', '/var/log/innostatus')
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    log_file = os.path.join(LOGS_DIR, 'audit.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(message)s'))
    audit_logger.addHandler(file_handler)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    return request.headers.get("User-Agent", "unknown")


def log_security_event(
    event_type: str,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request: Optional[Request] = None,
    status: str = "success"
):
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'user_id': user_id,
        'status': status,
        'ip_address': get_client_ip(request) if request else None,
        'user_agent': get_user_agent(request) if request else None,
        'details': details or {}
    }
    
    audit_logger.info(json.dumps(log_entry, ensure_ascii=False))



def log_login(user_id: str, request: Request, status: str = "success", failure_reason: Optional[str] = None):
    details = {}
    if failure_reason:
        details['failure_reason'] = failure_reason
    
    log_security_event(
        event_type='login',
        user_id=user_id,
        details=details,
        request=request,
        status=status
    )


def log_register(user_id: str, request: Request, email: str):
    log_security_event(
        event_type='register',
        user_id=user_id,
        details={'email': email},
        request=request,
        status='success'
    )


def log_password_change(user_id: str, request: Request, status: str = "success"):
    log_security_event(
        event_type='password_change',
        user_id=user_id,
        details={},
        request=request,
        status=status
    )


def log_password_reset_request(email: str, request: Request):
    log_security_event(
        event_type='password_reset_request',
        details={'email': email},
        request=request,
        status='success'
    )


def log_check_performed(user_id: str, request: Request, check_type: str, text_length: int = 0, api_key_id: Optional[str] = None):
    log_security_event(
        event_type='check_performed',
        user_id=user_id,
        details={
            'check_type': check_type,
            'text_length': text_length,
            'api_key_id': api_key_id
        },
        request=request,
        status='success'
    )


def log_api_key_created(user_id: str, request: Request, key_id: str, key_type: str):
    log_security_event(
        event_type='api_key_created',
        user_id=user_id,
        details={
            'key_id': key_id,
            'key_type': key_type
        },
        request=request,
        status='success'
    )


def log_api_key_used(user_id: str, request: Request, key_id: str, check_id: str):
    log_security_event(
        event_type='api_key_used',
        user_id=user_id,
        details={
            'key_id': key_id,
            'check_id': check_id
        },
        request=request,
        status='success'
    )


def log_profile_update(user_id: str, request: Request, fields_updated: list):
    log_security_event(
        event_type='profile_update',
        user_id=user_id,
        details={'fields_updated': fields_updated},
        request=request,
        status='success'
    )


def log_data_export(user_id: str, request: Request, export_type: str):
    log_security_event(
        event_type='data_export',
        user_id=user_id,
        details={'export_type': export_type},
        request=request,
        status='success'
    )


def log_failed_auth_attempt(identifier: str, request: Request, failure_reason: str):
    log_security_event(
        event_type='failed_auth_attempt',
        details={
            'identifier': identifier,  # email или username
            'failure_reason': failure_reason
        },
        request=request,
        status='failure'
    )


def log_suspicious_activity(user_id: Optional[str], request: Request, activity_type: str, details: Dict[str, Any]):
    log_security_event(
        event_type='suspicious_activity',
        user_id=user_id,
        details={
            'activity_type': activity_type,
            **details
        },
        request=request,
        status='warning'
    )
