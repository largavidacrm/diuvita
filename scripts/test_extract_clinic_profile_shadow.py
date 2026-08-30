#!/usr/bin/env python3
"""Basic checks for the shadow clinic profile extractor."""
from capture_source_snapshot import FetchResult
from extract_clinic_profile_shadow import extract_from_fetch, extract_professionals


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
  <p>Pruebas disponibles: DEXA, VO2 max, biomarcadores y test epigenético.</p>
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
    check("VO2 max" in profile["technologies"], "technology detection failed")
    check("Hipoxia intermitente" in profile["technologies"], "later-page technology detection failed")
    check("Medicina preventiva" in profile["services"], "service detection failed")
    check("Unidad de Longevidad" in profile["units"], "unit detection failed")
    check("Dra. Laura García Pérez" in profile["professionals"], "professional detection failed")
    check("contact.email" in fields, "email claim missing")
    check("units.list" in fields, "unit claim missing")
    check("professionals.published" in fields, "professional claim missing")
    check(extraction["rule_decisions"], "rule decisions missing")

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
