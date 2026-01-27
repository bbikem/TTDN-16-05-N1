{
    "name": "Chatbot tính lương",
    "version": "15.0.1.0.0",
    "category": "Human Resources",
    "summary": "Chatbot tính lương dùng Groq API, rules từ file md",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/payroll_chat_views.xml"
    ],
    "installable": True,
}