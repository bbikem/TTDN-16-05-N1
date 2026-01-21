{
    "name": "Nhân sự (Core)",
    "version": "15.0.1.0.0",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail"   # ✅ BẮT BUỘC
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/chuc_vu.xml",
        "views/phong_ban.xml",
        "views/nhan_vien.xml",
        "views/chung_chi.xml",
        "views/lich_su_cong_tac.xml",
        "views/menu.xml",
    ],
    "application": True,
}
