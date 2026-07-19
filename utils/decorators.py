# ==============================================================
# المزخرفات والتحقق من الصلاحيات
# ==============================================================
from functools import wraps
from flask import redirect, url_for, flash, g, abort
from utils.auth import current_user, has_permission


def login_required(f):
    """
    مزخرف للتحقق من تسجيل الدخول
    
    الوصف:
    يتحقق من أن المستخدم قد قام بتسجيل الدخول.
    إذا لم يكن مسجلاً، يعيد توجيهه إلى صفحة تسجيل الدخول.
    
    الاستخدام:
    @login_required
    def dashboard():
        ...
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            flash("يرجى تسجيل الدخول أولاً", "error")
            return redirect(url_for("auth.login"))
        
        # تخزين المستخدم في g لاستخدامه في الدالة
        g.user = user
        return f(*args, **kwargs)
    
    return wrapper


def permission_required(permission_name):
    """
    مزخرف للتحقق من صلاحية معينة
    
    الوصف:
    يتحقق من أن المستخدم الحالي لديه الصلاحية المطلوبة.
    إذا لم يكن لديه الصلاحية، يعرض رسالة خطأ ويعيد التوجيه.
    
    المعاملات:
    permission_name : اسم الصلاحية (مثل: can_approve_purchases)
    
    الاستخدام:
    @permission_required('can_approve_purchases')
    def approve_invoice():
        ...
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def wrapper(*args, **kwargs):
            if not has_permission(permission_name):
                flash("ليست لديك صلاحية لهذا الإجراء", "error")
                return redirect(url_for("dashboard.index"))
            return f(*args, **kwargs)
        
        return wrapper
    
    return decorator


def admin_required(f):
    """
    مزخرف للتحقق من أن المستخدم مدير
    
    الوصف:
    يتحقق من أن المستخدم لديه صلاحية إدارة المستخدمين
    (عادة ما يكون المدير فقط).
    
    الاستخدام:
    @admin_required
    def manage_users():
        ...
    """
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if not has_permission('can_manage_users'):
            flash("هذا الإجراء متاح للمديرين فقط", "error")
            return redirect(url_for("dashboard.index"))
        return f(*args, **kwargs)
    
    return wrapper


def json_request(f):
    """
    مزخرف للتحقق من أن الطلب يحتوي على JSON صحيح
    
    الوصف:
    يتحقق من أن الطلب يحتوي على بيانات JSON صحيحة.
    
    الاستخدام:
    @json_request
    def api_endpoint():
        ...
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        from flask import request, jsonify
        
        if not request.is_json:
            return jsonify({'ok': False, 'error': 'يجب أن يكون الطلب بصيغة JSON'}), 400
        
        return f(*args, **kwargs)
    
    return wrapper
