"""
routes — حزمة المسارات (Routes Package)
تسجيل كل الـ Blueprints في تطبيق Flask
"""


def register_blueprints(app):
    """تسجيل كل الـ Blueprints في التطبيق"""
    # التأخير في الاستيراد لتفادي المشاكل الدائرية
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.items import items_bp
    from routes.suppliers import suppliers_bp
    from routes.customers import customers_bp
    from routes.purchases import purchases_bp
    from routes.disbursement import disbursement_bp
    from routes.writeoff import writeoff_bp
    from routes.users import users_bp
    from routes.reports import reports_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(items_bp)
    app.register_blueprint(suppliers_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(purchases_bp)
    app.register_blueprint(disbursement_bp)
    app.register_blueprint(writeoff_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(api_bp)
