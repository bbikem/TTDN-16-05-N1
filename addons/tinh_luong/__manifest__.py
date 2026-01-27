# -*- coding: utf-8 -*-
{
    "name": "Tính lương",
    "version": "15.0.1.0.0",
    "category": "Human Resources",
    "summary": "Tính lương dựa trên Nhân sự & Chấm công",
    "depends": [
        "base",
        "nhan_su",
        "cham_cong",
        "google_calendar",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence.xml",
        "views/menu.xml",
        "views/ngay_tra_luong_views.xml",
        "views/tro_cap_views.xml",
        "views/bang_luong_views.xml",
    ],
    "installable": True,
    "application": True,
}
