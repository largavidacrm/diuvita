#!/usr/bin/env python3
"""Basic checks for the shadow clinic profile extractor."""
from capture_source_snapshot import FetchResult
from extract_clinic_profile_shadow import extract_from_fetch, extract_locations, extract_professionals


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
    check("contact.email" in fields, "email claim missing")
    check("location.locations" in fields, "location claim missing")
    check("units.list" in fields, "unit claim missing")
    check("professionals.published" in fields, "professional claim missing")
    check("transparency.years_in_practice" in fields, "years claim missing")
    check("transparency.specialists_count" in fields, "specialist count claim missing")
    check("team.credentialing_visible" in fields, "credentialing claim missing")
    check("prices.public_status" in fields, "pricing claim missing")
    check(extraction["rule_decisions"], "rule decisions missing")
    extracted_locations = extract_locations(
        "Sedes Calle Serrano 100, 28006 Madrid. Avenida Diagonal 450, 08006 Barcelona. Contacto"
    )
    check(len(extracted_locations) == 2, "location extractor should capture clear address patterns")
    check(
        all("Sede 1" not in str(item) and "Sede 2" not in str(item) for item in extracted_locations),
        "extracted locations should not create numbered labels",
    )

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
