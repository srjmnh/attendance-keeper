from flask import Blueprint
from datetime import datetime

def init_filters(app):
    """Initialize custom Jinja2 filters"""
    
    @app.template_filter('split')
    def split_filter(value, delimiter):
        """Split a string by delimiter"""
        if value is None:
            return []
        return str(value).split(delimiter)
    
    @app.template_filter('first')
    def first_filter(value):
        """Get first element of a list"""
        if not value:
            return None
        return value[0] if len(value) > 0 else None 
    
    @app.template_filter('datetime')
    def format_datetime(value):
        """Format a datetime object or string to a readable format"""
        if not value:
            return ''
        try:
            if isinstance(value, datetime):
                dt = value
            else:
                dt = datetime.fromisoformat(str(value))
            return dt.strftime('%Y-%m-%d %H:%M')
        except (ValueError, TypeError):
            return str(value)
    
    @app.template_filter('current_year')
    def current_year_filter(text):
        """Return the current year."""
        return datetime.now().year
    
    # Return the app to ensure filters are registered
    return app 