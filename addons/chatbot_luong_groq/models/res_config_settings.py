from odoo import api, fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    groq_api_key = fields.Char(string="Groq API Key", config_parameter="chatbot_luong_groq.groq_api_key")
    groq_model = fields.Char(string="Groq Model", default="llama-3.1-8b-instant",
                             config_parameter="chatbot_luong_groq.groq_model")
