#!/usr/bin/env python3
"""Basic checks for the shadow clinic profile extractor."""
from capture_source_snapshot import FetchResult
from extract_clinic_profile_shadow import (
    extract_contacts,
    extract_from_fetch,
    extract_locations,
    extract_professionals,
    extract_years_in_practice,
)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    filler = " ".join(["relleno"] * 260)
    html = f"""
<!doctype html>
<html>
<head><title>Example Longevity Clinic | Barcelona</title></head>
<body>
  <h1>Example Longevity Clinic</h1>
  <p>Medicina preventiva, longevidad, nutrición y medicina del sueño.</p>
  <p>Unidad de Longevidad dirigida por Dra. Laura García Pérez.</p>
  <p>Más de 20 años de experiencia y equipo de 12 especialistas.</p>
  <p>Dra. Laura García Pérez, nº colegiada 12345.</p>
  <p>Precio consulta: 120 €.</p>
  <p>Pruebas disponibles: DEXA, VO2 max, biomarcadores y test epigenético.</p>
  <p>Sedes: Calle Serrano 100, 28006 Madrid. Avenida Diagonal 450, 08006 Barcelona.</p>
  <p>{filler}</p>
  <p>Programa con hipoxia intermitente.</p>
  <p>Contacto: info@exampleclinic.test +34 930 111 222 @exampleclinic</p>
</body>
</html>
""".encode("utf-8")
    extraction = extract_from_fetch(
        FetchResult(
            source_url="https://exampleclinic.test/longevidad",
            final_url="https://exampleclinic.test/longevidad",
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=html,
        )
    )
    profile = extraction["candidate_profile"]
    fields = {claim["field_path"]: claim for claim in extraction["field_claims"]}
    check(profile["name"] == "Example Longevity Clinic", "name guess failed")
    check(profile["emails"] == ["info@exampleclinic.test"], "email extraction failed")
    check(profile["instagram"] == ["@exampleclinic"], "instagram extraction failed")
    check(
        extract_contacts("Contacto 919703393 646039428")["phones"] == ["919703393", "646039428"],
        "adjacent Spanish phone numbers should be split",
    )
    check(
        extract_contacts("Contacto +34965130120 965210687")["phones"] == ["+34965130120", "965210687"],
        "adjacent +34 and Spanish phone numbers should be split",
    )
    check(
        extract_contacts("Medicina General COMB 08-29679-5")["phones"] == [],
        "professional registry numbers should not be extracted as phones",
    )
    check(len(profile["locations"]) == 2, "two locations should be extracted")
    check(profile["locations"][0]["city"] == "Madrid", "Madrid location city missing")
    check(profile["locations"][1]["city"] == "Barcelona", "Barcelona location city missing")
    check("VO2 max" in profile["technologies"], "technology detection failed")
    check("Hipoxia intermitente" in profile["technologies"], "later-page technology detection failed")
    check("Medicina preventiva" in profile["services"], "service detection failed")
    check("Unidad de Longevidad" in profile["units"], "unit detection failed")
    check("Dra. Laura García Pérez" in profile["professionals"], "professional detection failed")
    check(profile["years_in_practice"] == "más de 20 años", "years in practice detection failed")
    check(profile["specialists_count"] == 12, "specialist count detection failed")
    check(profile["team_credentialing_visible"] == "si", "credentialing visibility detection failed")
    check(profile["public_pricing"] == "si", "public pricing detection failed")
    check(
        extract_years_in_practice("Con experiencia de más de una década y miles de clientes") == "más de 10 años",
        "textual decade experience should be normalized",
    )
    check(
        extract_years_in_practice("Dos décadas de experiencia clínica") == "20 años",
        "decades should be converted to years",
    )
    check("contact.email" in fields, "email claim missing")
    check("location.locations" in fields, "location claim missing")
    check("units.list" in fields, "unit claim missing")
    check("professionals.published" in fields, "professional claim missing")
    check("transparency.years_in_practice" in fields, "years claim missing")
    check("transparency.specialists_count" in fields, "specialist count claim missing")
    check("team.credentialing_visible" in fields, "credentialing claim missing")
    check("prices.public_status" in fields, "pricing claim missing")
    check(extraction["rule_decisions"], "rule decisions missing")
    imda_contact_html = """
<!doctype html>
<html>
<head><title>Unidad de longevidad - Instituto de Medicina y Dermatología Avanzada</title></head>
<body>
  <input id="main-menu-state" class="main-menu-toggle" type="checkbox">
  <main><h1>Unidad de Longevidad</h1></main>
  <footer>
    <a href="mailto:contact@mysite.com"><span>info@imda.es</span></a>
    <a href="tel:123-456-7890"><span>676 629 862</span></a>
    <a href="tel:123-456-7890"><span>91 6325659</span></a>
    <span>C/ Goya 5-7, entreplanta. Entrada por pasaje comercial 28001, Madrid</span>
  </footer>
</body>
</html>
""".encode("utf-8")
    imda_extraction = extract_from_fetch(
        FetchResult(
            source_url="https://www.imda.es/unidades/unidad-de-longevidad/",
            final_url="https://www.imda.es/unidades/unidad-de-longevidad/",
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=imda_contact_html,
        )
    )
    imda_profile = imda_extraction["candidate_profile"]
    imda_fields = {claim["field_path"]: claim for claim in imda_extraction["field_claims"]}
    check(imda_profile["emails"] == ["info@imda.es"], "IMDA visible email should be extracted")
    check(imda_profile["phones"] == ["676629862", "916325659"], "IMDA visible phones should be extracted")
    check(imda_fields["contact.phone"]["value"] == "676629862", "IMDA primary phone claim missing")
    check(imda_fields["contact.phone_fixed"]["value"] == "916325659", "IMDA fixed phone claim missing")
    check("contact.phone_mobile" not in imda_fields, "primary mobile phone should not be duplicated")
    extracted_locations = extract_locations(
        "Sedes Calle Serrano 100, 28006 Madrid. Avenida Diagonal 450, 08006 Barcelona. Contacto"
    )
    check(len(extracted_locations) == 2, "location extractor should capture clear address patterns")
    check(
        all("Sede 1" not in str(item) and "Sede 2" not in str(item) for item in extracted_locations),
        "extracted locations should not create numbered labels",
    )
    duplicate_location = extract_locations(
        "Dirección: Avda. Blasco Ibáñez 14 46010 Valencia. "
        "Hospital Quirónsalud Valencia Avda. Blasco Ibáñez, 14 46010 Valencia Valencia."
    )
    check(len(duplicate_location) == 1, "near-duplicate location addresses should be collapsed")
    imda_locations = extract_locations(
        "Dirección: C/ Goya 5-7, entreplanta. Entrada por pasaje comercial 28001, Madrid. "
        "Almudena Nuño ® Copyright 2026 | Teléfonos de contacto: 676 629 862 y 91 6325659"
    )
    check(len(imda_locations) == 1, "IMDA-style split address should be extracted")
    check(imda_locations[0]["city"] == "Madrid", "IMDA city should be detected")
    check(
        imda_locations[0]["address"] == "C/ Goya 5-7, entreplanta. Entrada por pasaje comercial 28001, Madrid",
        "IMDA address should keep postcode and access note",
    )

    long_intro = " ".join(["navigation"] * 520)
    tiara_team_html = f"""
<!doctype html>
<html>
<head><title>Our Team of Experts TIARA HEALTH</title></head>
<body>
  <p>{long_intro}</p>
  <main>
    <h1>Our Team of Experts</h1>
    <p>Dr. Francisco Martinez University Seville Bachelor Medicine</p>
    <p>Dr. Esmail Sheybani Geneva longevity physician</p>
    <p>Dr. Ryan Lukas Farhad is a specialist in sports medicine</p>
    <p>Dr. Joseph Crespo London-based Private Outpatients Department</p>
    <p>Contact info@tiarahealth.com +34 682 269 673</p>
  </main>
</body>
</html>
""".encode("utf-8")
    tiara_extraction = extract_from_fetch(
        FetchResult(
            source_url="https://www.tiarahealth.com/our-team-of-experts/",
            final_url="https://www.tiarahealth.com/our-team-of-experts/",
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=tiara_team_html,
        )
    )
    tiara_profile = tiara_extraction["candidate_profile"]
    tiara_fields = {claim["field_path"]: claim for claim in tiara_extraction["field_claims"]}
    check("name" not in tiara_profile, "team-page title should not become clinic identity")
    check(tiara_profile["emails"] == ["info@tiarahealth.com"], "team-page email should survive focused excerpt")
    check(tiara_profile["phones"] == ["+34 682 269 673"], "team-page phone should survive focused excerpt")
    check(
        tiara_profile["professionals"] == [
            "Dr. Francisco Martinez",
            "Dr. Esmail Sheybani",
            "Dr. Ryan Lukas Farhad",
            "Dr. Joseph Crespo",
        ],
        "long English team page should produce clean professional proposals",
    )
    check("identity.canonical_name" not in tiara_fields, "team-page title should not create identity claim")

    regenera_text = (
        "NUESTRO EQUIPO Te acompañamos desde la ciencia y la empatía "
        "Dra. Délia Vilá Dirección Xavier Carretero Gerente / Nutrición "
        "Neli Martínez Subdirectora Dra. Andrea Briceño Medicina Estética y Longevidad "
        "Dr. Ignacio Viza Otorrinolaringología Dr. Marc Bausili Anestesia "
        "Dra. Emilce Pérez Flebología Dra. Lidia Sánchez Porro Cirugía Plástica "
        "Jenny Bernal Atención al Paciente Micaela Arenas Técnico Auxiliar "
        "Marina Martín Responsable RRSS Contáctanos"
    )
    regenera_professionals = extract_professionals(regenera_text)
    check("Dra. Délia Vilá" in regenera_professionals, "titled professional should stop before role")
    check("Xavier Carretero" in regenera_professionals, "role-paired professional missing")
    check("Neli Martínez" in regenera_professionals, "non-titled professional missing")
    check("Dr. Marc Bausili" in regenera_professionals, "next titled professional missing")
    check("Dra. Lidia Sánchez Porro" in regenera_professionals, "compound surname missing")
    check("Jenny Bernal" in regenera_professionals, "patient-care team member missing")
    check("Micaela Arenas" in regenera_professionals, "technical assistant team member missing")
    check("Marina Martín" in regenera_professionals, "social media team member missing")
    check(len(regenera_professionals) == 11, "all Regenera-style team entries should be detected")
    check(
        all("Dirección Xavier" not in item for item in regenera_professionals),
        "role and next name should not merge",
    )

    sha_professionals = extract_professionals(
        "Nuestro equipo Dr. GUILLERMO TORRE Cardiólogo "
        "Dra. JESSICA SHEPHERD Ginecóloga Contacto"
    )
    check("Dr. GUILLERMO TORRE" in sha_professionals, "cardiology role should not merge into name")
    check("Dra. JESSICA SHEPHERD" in sha_professionals, "gynecology role should not merge into name")
    check(
        all("Cardiólogo" not in item and "Ginecóloga" not in item for item in sha_professionals),
        "medical role should not be part of extracted names",
    )

    neolife_menu_professionals = extract_professionals(
        "NUESTRO EQUIPO FRANQUICIAS SUPLEMENTOS ANTIAGING BLOG "
        "TRATAMIENTOS MÉTODO NEOLIFE CHEQUEOS PREVENTIVOS PROGRAMAS DE SEGUIMIENTO "
        "TRATAMIENTOS PARA HOMBRE MICROBIOTA NUTRICIÓN BENEFICIOS PILARES NEOLIFE TESTIMONIOS"
    )
    check(
        "TRATAMIENTOS PARA HOMBRE MICROBIOTA" not in neolife_menu_professionals,
        "uppercase treatment menu should not become a professional",
    )

    imda_professionals = extract_professionals(
        "Nuestro equipo Dra. Almudena Nuño Dermatología "
        "Dr. Francisco Kerdel Unidad de Longevidad Contacto"
    )
    check("Dra. Almudena Nuño" in imda_professionals, "dermatology role should not merge into name")
    check("Dr. Francisco Kerdel" in imda_professionals, "unit section should not merge into name")
    check(
        all("Unidad" not in item and "Dermatología" not in item for item in imda_professionals),
        "unit or role text should not be part of extracted names",
    )
    imda_archive_professionals = extract_professionals(
        "Miembros Archivos: Miembros del equipo "
        "Maria María Ortega Enfermera / Responsable de Ensayos clínicos Ver Curriculum "
        "Laura Laura Ramos Auxiliar de enfermería/ Staff Ver Curriculum "
        "Luz Luz Mary Arias Auxiliar de enfermería/ Staff mary@imda.es Ver Curriculum "
        "Simona Simona Grigore Coordinadora de estética / Auxiliar de enfermería simona@imda.es Ver Curriculum "
        "Alejandra Alejandra Russo Gerente administrativo / Coordinadora del área de atencion al paciente alejandra@imda.es Ver Curriculum "
        "Lucía F Lucía Fernández Radióloga y Médico Estético Ver Curriculum "
        "Beatriz Beatriz Martínez Cirujana vascular / Médico Estético beatriz@imda.es @dr.beatrizmturegano Ver Curriculum "
        "Lucero lucero noguera Dermatóloga / Dermatóloga pediátrica lucero@imda.es Ver Curriculum "
        "Giulia Giulia Dradi Dermatóloga y Médico Estético giulia@imda.es Ver Curriculum "
        "Sergio SERGIO MOTA Traumatólogo sergio@imda.es Ver Curriculum"
    )
    check("María Ortega" in imda_archive_professionals, "IMDA archive nurse should be captured cleanly")
    check("Luz Mary Arias" in imda_archive_professionals, "IMDA archive repeated first name should be repaired")
    check("Lucía Fernández" in imda_archive_professionals, "IMDA archive initial label should be removed")
    check("Lucero Noguera" in imda_archive_professionals, "IMDA lowercase repeated name should be normalized")
    check("Sergio Mota" in imda_archive_professionals, "IMDA uppercase repeated name should be normalized")
    check(len(imda_archive_professionals) == 10, "IMDA archive should produce ten clean public team names")
    check(
        all(
            "Curriculum" not in item
            and "Staff" not in item
            and "Médico" not in item
            and "Dermatóloga" not in item
            and "@" not in item
            for item in imda_archive_professionals
        ),
        "IMDA archive roles and contact fragments should not be part of names",
    )

    arvila_professionals = extract_professionals(
        "Equipo de Arvila Magna Dr. Jordi Ibañez Chequeos de Longevidad "
        "Dr. Joan Josep Fuertes Medicina General COMB 08-29679-5 "
        "Dr. Pere Gascón Oncología Integrativa COMB 8.560 "
        "Dra. Mariana Díaz Dermatología Estética COMB 47856 "
        "Conoce al Dr. Jordi Ibañez ¿Qué te ofrecemos? Contacto"
    )
    check("Dr. Jordi Ibañez" in arvila_professionals, "navigation label should not merge into Jordi Ibañez")
    check("Dr. Joan Josep Fuertes" in arvila_professionals, "medical role should not merge into Joan Josep Fuertes")
    check("Dr. Pere Gascón" in arvila_professionals, "oncology role should not merge into Pere Gascón")
    check("Dra. Mariana Díaz" in arvila_professionals, "dermatology role should not merge into Mariana Díaz")
    check(
        sum(1 for item in arvila_professionals if item.lower().replace("ñ", "n") == "dr. jordi ibanez") == 1,
        "accent variants should dedupe to one professional",
    )
    check(
        all(
            "Chequeos" not in item
            and "Oncología" not in item
            and "COMB" not in item
            and "Dermatología" not in item
            and "Qué" not in item
            for item in arvila_professionals
        ),
        "Arvila role/context text should not be part of extracted names",
    )

    untitled_team_professionals = extract_professionals(
        "Equipo médico Jordi Ibañez Chequeos de Longevidad "
        "Joan Josep Fuertes Medicina General "
        "Pere Gascón Oncología Integrativa "
        "Mariana Díaz Dermatología Estética Contacto"
    )
    check("Jordi Ibañez" in untitled_team_professionals, "untitled longevity-check doctor should be captured")
    check("Joan Josep Fuertes" in untitled_team_professionals, "untitled general-medicine doctor should be captured")
    check("Pere Gascón" in untitled_team_professionals, "untitled integrative oncology doctor should be captured")
    check("Mariana Díaz" in untitled_team_professionals, "untitled dermatology doctor should be captured")
    check(
        all("Medicina" not in item and "Dermatología" not in item and "Chequeos" not in item for item in untitled_team_professionals),
        "untitled team roles should not be part of extracted names",
    )
    arvila_menu_professionals = extract_professionals(
        "Equipo Áreas Osteopatía Ginecología Integrativa Longevidad Dr. Jordi Ibañez "
        "Chequeos de Longevidad Hipoxia Intermitente Select Page "
        "Equipo de la Clínica de Medicina Integrativa en Barcelona Arvila Magna "
        "D.O. Quim Vicent Director de la Clínica "
        "Agenda tu Cita con Quim Equipo de Arvila Magna "
        "Dr. Joan Josep Fuertes Medicina General COMB 08-29679-5 Agenda tu Cita con Joan "
        "Dra. Mariana Díaz Dermatología Estética COMB 47856 Agenda tu Cita con Mariana "
        "Marta Pradell Fisioterapeuta CFC 12370 Agenda tu Cita con Marta "
        "Silvia Naranjo Óptica Optometrista CNOO 11618 Contacto"
    )
    check("D.O. Quim Vicent" in arvila_menu_professionals, "D.O. professional should be captured")
    check("Marta Pradell" in arvila_menu_professionals, "CTA text should not merge adjacent professionals")
    check("Silvia Naranjo" in arvila_menu_professionals, "attached optical role should be trimmed")
    check(
        all("Hipoxia" not in item and "PNIE" not in item and "Óptica" not in item for item in arvila_menu_professionals),
        "menu or attached role text should not become professionals",
    )
    arvila_tail_professionals = extract_professionals(
        "Equipo médico Gerardo Camors Auxiliar Jordi Gallifa Gerente Esther Pedrol Recepción "
        "Osteopatía Osteopatía Deportiva Osteopatía Ginecológica Osteopatía Pediátrico "
        "Médicina Medicina Integrativa Analítica de Frotis Sanguíneo "
        "Nutrición Integrativa PNIE Fisioterapia Contacto"
    )
    check("Gerardo Camors" in arvila_tail_professionals, "assistant name should be captured before role")
    check("Jordi Gallifa" in arvila_tail_professionals, "manager name should be captured before role")
    check("Esther Pedrol" in arvila_tail_professionals, "reception name should be captured before role")
    check(
        all("Osteopatía" not in item and "PNIE" not in item and "Médicina" not in item for item in arvila_tail_professionals),
        "service-list tail should not become professionals",
    )

    kairos_professionals = extract_professionals(
        "Conoce nuestro equipo Dra. Anna Paola Medicina Estética Regenerativa y Longevidad "
        "Dra. Marieta Ramírez Ginecología regenerativa y Salud integral de la mujer "
        "Dr. Manuel Lujan Neurofisiólogo clínico, experto en medicina del sueño. "
        "Lic. Carolina Toledo Nutrición funcional Dra. Ivanna Gonzalez Medicina Interna "
        "Lic. María Sanchez Vecino Nutricionista y experta en Microbiota "
        "Graciela García Atención al paciente Contacto"
    )
    check("Dra. Anna Paola" in kairos_professionals, "Kairos doctor should stop before specialty")
    check("Dra. Marieta Ramírez" in kairos_professionals, "Kairos gynecology role should not merge")
    check("Dr. Manuel Lujan" in kairos_professionals, "Kairos neurophysiology role should not merge")
    check("Lic. Carolina Toledo" in kairos_professionals, "Lic. title should be captured")
    check("Lic. María Sanchez Vecino" in kairos_professionals, "Lic. nutritionist should be captured")
    check(
        all(
            "Neurofisiólogo" not in item
            and "Medicina" not in item
            and "Nutricionista" not in item
            and "Microbiota" not in item
            for item in kairos_professionals
        ),
        "Kairos role/context text should not be part of extracted names",
    )

    noisy_title_html = b"""
<!doctype html>
<html>
<head><title>RegeneraClinic nace de la pasion por adaptarse a envejecer de forma natural</title></head>
<body>
  <p>NUESTRO EQUIPO Dra. Example Name Direccion Contacto</p>
</body>
</html>
"""
    noisy = extract_from_fetch(
        FetchResult(
            source_url="https://regeneraclinic.example/quienes-somos",
            final_url="https://regeneraclinic.example/quienes-somos",
            status_code=200,
            content_type="text/html; charset=utf-8",
            body=noisy_title_html,
        )
    )
    noisy_fields = {claim["field_path"] for claim in noisy["field_claims"]}
    check("name" not in noisy["candidate_profile"], "noisy title should not become profile name")
    check("identity.canonical_name" not in noisy_fields, "noisy title should not become identity claim")
    print("OK extraction: shadow clinic profile")


if __name__ == "__main__":
    main()
