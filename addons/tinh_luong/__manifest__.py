{
    "name": "Tính Lương (Payroll)",
    "version": "15.0.1.0.0",
    "license": "LGPL-3",
    "category": "Human Resources",
    "depends": [
        "nhan_su",
        "cham_cong",
        "mail"  
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/ai_rule.xml",
        "views/khau_tru_luong.xml",
        "views/bang_luong.xml",
        "views/thanh_toan_luong.xml",
        "views/menu.xml",
    ],
    "installable": True,
    "application": True,
    "summary": """
        Module tính lương tự động từ chấm công, quản lý khấu trừ,
        bảo hiểm, thưởng và thanh toán lương
    """,
}
