from flask import Blueprint

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