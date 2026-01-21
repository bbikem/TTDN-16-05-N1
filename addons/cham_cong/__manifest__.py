# -*- coding: utf-8 -*-
{
    'name': "Chấm Công (Attendance)",

    'summary': """
        Module quản lý chấm công, tính công, đơn từ xin phép/đi muộn/về sớm
    """,

    'description': """
        Tính năng:
        - Quản lý ca làm theo ngày
        - Bảng chấm công với tính toán tự động
        - Xác định trạng thái: đi làm, đi muộn, về sớm, vắng mặt
        - Quản lý đơn từ (xin phép, đi muộn, về sớm)
        - Tính công tự động (công cơ bản, OT)
        - Khóa bảng chấm công khi tính công
        - Báo cáo thống kê chấm công
    """,

    'author': "Fitdnu",
    'website': "http://www.fitdnu.com",

    'category': 'Human Resources',
    'version': '15.0.1.0.0',

    'depends': [
        'base',
        'nhan_su',
        'mail'
    ],

    'data': [
        'data/sequence_data.xml',
        'security/ir.model.access.csv',
        'views/dang_ky_ca_lam_theo_ngay.xml',
        'views/bang_cham_cong.xml',
        'views/dot_dang_ky.xml',
        'views/don_tu.xml',
        'views/tinh_cong.xml',
        'views/menu.xml',
    ],
    
    'installable': True,
    'application': True,
}
