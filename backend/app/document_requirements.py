PENSION_DOCUMENT_REQUIREMENTS = {
    "retirement_standard": {
        "display_name": "Страховая пенсия по старости",
        "description": "Назначается при достижении определенного возраста, наличии необходимого стажа и пенсионных баллов.",
        "documents": [
            {"id": "passport_rf", "name": "Паспорт РФ", "ocr_type": "passport_rf", "is_critical": True, "description": "Основной документ, удостоверяющий личность.", "condition_text": None},
            {"id": "snils", "name": "СНИЛС", "ocr_type": "snils_card", "is_critical": True, "description": "Страховой номер индивидуального лицевого счета.", "condition_text": None},
            {"id": "work_book", "name": "Трудовая книжка (или сведения о трудовой деятельности)", "ocr_type": "work_book_page", "is_critical": True, "description": "Подтверждение трудового стажа.", "condition_text": None},
            {"id": "birth_certificate_children", "name": "Свидетельство о рождении ребенка (детей)", "ocr_type": None, "is_critical": False, "description": "Для учета периода ухода за детьми в стаж.", "condition_text": "при учете периода ухода за детьми в стаж"},
            {"id": "military_id", "name": "Военный билет", "ocr_type": None, "is_critical": False, "description": "Для учета периода военной службы в стаже.", "condition_text": "для учета периода военной службы в стаже (для мужчин)"},
            {"id": "marriage_certificate", "name": "Свидетельство о браке/расторжении/смене имени", "ocr_type": None, "is_critical": False, "description": "Для подтверждения смены ФИО.", "condition_text": "при смене ФИО"},
            {"id": "salary_certificate_2002", "name": "Справка о заработке за 60 месяцев до 01.01.2002", "ocr_type": None, "is_critical": False, "description": "Для возможного увеличения размера пенсии при наличии стажа до 2002 года.", "condition_text": "при наличии стажа до 2002 года"},
            {"id": "special_work_conditions_proof", "name": "Справка, уточняющая особый характер работы или условий труда", "ocr_type": None, "is_critical": False, "description": "Для досрочного назначения пенсии.", "condition_text": "при наличии периодов работы, дающих право на досрочную пенсию"},
            {"id": "application", "name": "Заявление о назначении пенсии", "ocr_type": None, "is_critical": True, "description": "Заявление установленной формы.", "condition_text": None}
        ]
    },
    "disability_insurance": {
        "display_name": "Страховая пенсия по инвалидности",
        "description": "Назначается лицам, признанным инвалидами, при наличии хотя бы одного дня страхового стажа.",
        "documents": [
            {"id": "passport_rf", "name": "Паспорт РФ", "ocr_type": "passport_rf", "is_critical": True, "description": "Основной документ, удостоверяющий личность.", "condition_text": None},
            {"id": "snils", "name": "СНИЛС", "ocr_type": "snils_card", "is_critical": True, "description": "Страховой номер индивидуального лицевого счета.", "condition_text": None},
            {"id": "mse_certificate", "name": "Справка МСЭ об установлении инвалидности", "ocr_type": "mse_certificate", "is_critical": True, "description": "Основной документ, подтверждающий инвалидность.", "condition_text": None},
            {"id": "work_book", "name": "Трудовая книжка (при наличии, для подтверждения факта стажа)", "ocr_type": "work_book_page", "is_critical": False, "description": "Подтверждение трудового стажа, если имеется.", "condition_text": None},
            {"id": "application", "name": "Заявление о назначении пенсии", "ocr_type": None, "is_critical": True, "description": "Заявление установленной формы.", "condition_text": None}
        ]
    },
    "disability_social": {
        "display_name": "Социальная пенсия по инвалидности",
        "description": "Назначается инвалидам, не имеющим права на страховую пенсию (стаж не требуется).",
        "documents": [
            {"id": "passport_rf", "name": "Паспорт РФ", "ocr_type": "passport_rf", "is_critical": True, "description": "Основной документ, удостоверяющий личность.", "condition_text": None},
            {"id": "snils", "name": "СНИЛС", "ocr_type": "snils_card", "is_critical": True, "description": "Страховой номер индивидуального лицевого счета.", "condition_text": None},
            {"id": "mse_certificate", "name": "Справка МСЭ об установлении инвалидности", "ocr_type": "mse_certificate", "is_critical": True, "description": "Основной документ, подтверждающий инвалидность.", "condition_text": None},
            {"id": "residence_proof", "name": "Документ, подтверждающий постоянное проживание в РФ", "ocr_type": None, "is_critical": False, "description": "Требуется, если факт проживания не очевиден из паспорта.", "condition_text": "если не очевидно из паспорта"},
            {"id": "application", "name": "Заявление о назначении пенсии", "ocr_type": None, "is_critical": True, "description": "Заявление установленной формы.", "condition_text": None}
        ]
    },
    "survivor_benefit": {
         "display_name": "Пенсия по случаю потери кормильца",
         "description": "Назначается нетрудоспособным членам семьи умершего кормильца.",
         "documents": [
             {"id": "applicant_passport_rf", "name": "Паспорт заявителя (получателя пенсии)", "ocr_type": "passport_rf", "is_critical": True, "description": "Паспорт лица, обращающегося за пенсией.", "condition_text": None},
             {"id": "applicant_snils", "name": "СНИЛС заявителя (получателя пенсии)", "ocr_type": "snils_card", "is_critical": True, "description": "СНИЛС лица, обращающегося за пенсией.", "condition_text": None},
             {"id": "death_certificate", "name": "Свидетельство о смерти кормильца", "ocr_type": None, "is_critical": True, "description": "Документ, подтверждающий факт смерти кормильца.", "condition_text": None},
             {"id": "relationship_proof", "name": "Документы, подтверждающие родственные отношения с умершим (свидетельство о рождении, о браке)", "ocr_type": None, "is_critical": True, "description": "Подтверждение семейных связей с кормильцем.", "condition_text": None},
             {"id": "dependency_proof", "name": "Документы, подтверждающие нахождение на иждивении (если применимо)", "ocr_type": None, "is_critical": True, "description": "Если заявитель находился на иждивении умершего.", "condition_text": "если применимо"},
             {"id": "deceased_work_book", "name": "Трудовая книжка умершего кормильца (или иные документы о стаже)", "ocr_type": None, "is_critical": True, "description": "Для определения права на пенсию и ее размера.", "condition_text": None},
             {"id": "deceased_snils", "name": "СНИЛС умершего кормильца", "ocr_type": None, "is_critical": True, "description": "СНИЛС умершего кормильца.", "condition_text": None},
             {"id": "application", "name": "Заявление о назначении пенсии", "ocr_type": None, "is_critical": True, "description": "Заявление установленной формы.", "condition_text": None}
        ]
    }
}

# Карта для возможного использования на фронтенде для выбора типа пенсии
# Ключи здесь должны совпадать с ключами в PENSION_DOCUMENT_REQUIREMENTS
PENSION_TYPE_CHOICES = {
    "retirement_standard": "Страховая пенсия по старости",
    "disability_insurance": "Страховая пенсия по инвалидности",
    "disability_social": "Социальная пенсия по инвалидности",
    "survivor_benefit": "Пенсия по случаю потери кормильца" 
} 