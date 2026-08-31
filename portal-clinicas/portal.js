(function () {
  var config = window.VITALARGA_PORTAL_CONFIG || {};
  var clinics = Array.isArray(window.VITALARGA_PORTAL_CLINICS) ? window.VITALARGA_PORTAL_CLINICS : [];
  var client = null;
  var session = null;
  var workspace = { memberships: [], claim_requests: [], change_requests: [] };

  function el(id) {
    return document.getElementById(id);
  }

  function text(value) {
    return String(value == null ? "" : value);
  }

  function trimmed(id) {
    var node = el(id);
    return node ? text(node.value).trim() : "";
  }

  function html(value) {
    return text(value).replace(/[&<>"']/g, function (char) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[char];
    });
  }

  function show(node, visible) {
    if (!node) return;
    node.hidden = !visible;
    node.classList.toggle("hidden", !visible);
  }

  function setMessage(id, message, tone) {
    var node = el(id);
    if (!node) return;
    node.textContent = message || "";
    node.className = "portal-message" + (tone ? " " + tone : "");
  }

  function asUuid(value) {
    value = text(value).trim();
    return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value) ? value : null;
  }

  function splitLines(value) {
    return text(value).split(/\n|;/).map(function (line) {
      return line.trim();
    }).filter(Boolean);
  }

  function validUrlsFromTextarea(id) {
    return splitLines(trimmed(id)).filter(function (line) {
      return /^https?:\/\//i.test(line);
    });
  }

  function arrayToLines(value) {
    return Array.isArray(value) ? value.filter(Boolean).join("\n") : text(value).trim();
  }

  function normalizeComparable(value) {
    if (Array.isArray(value)) return JSON.stringify(value.map(function (item) { return text(item).trim(); }).filter(Boolean));
    return text(value).replace(/\s+/g, " ").trim();
  }

  function sameValue(beforeValue, afterValue) {
    return normalizeComparable(beforeValue) === normalizeComparable(afterValue);
  }

  function statusLabel(status) {
    var labels = {
      pending: "Pendiente",
      approved: "Aprobada",
      rejected: "Rechazada",
      needs_more_info: "Necesita más información",
      active: "Activo"
    };
    return labels[status] || status || "—";
  }

  function formatDate(value) {
    if (!value) return "";
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleDateString("es-ES", { day: "2-digit", month: "2-digit", year: "2-digit" });
  }

  function clinicLabel(clinic) {
    return [clinic.name, clinic.city, clinic.country].filter(Boolean).join(" · ");
  }

  function selectedClinic(selectId) {
    var select = el(selectId);
    if (!select) return null;
    var option = select.options[select.selectedIndex];
    if (!option) return null;
    var slug = option.getAttribute("data-slug");
    var id = option.getAttribute("data-id");
    return clinics.find(function (clinic) {
      return (slug && clinic.slug === slug) || (id && clinic.id === id);
    }) || null;
  }

  function selectedMembership() {
    var select = el("changeClinic");
    if (!select) return null;
    var id = select.value;
    return (workspace.memberships || []).find(function (membership) {
      return membership.clinic && membership.clinic.id === id;
    }) || null;
  }

  function populateClaimClinics() {
    var select = el("claimClinic");
    if (!select) return;
    var params = new URLSearchParams(window.location.search);
    var requestedSlug = params.get("claim") || "";
    var options = ['<option value="">Selecciona una ficha publicada</option>'].concat(clinics.map(function (clinic, index) {
      var value = clinic.slug || clinic.id || String(index);
      var selected = requestedSlug && requestedSlug === clinic.slug ? " selected" : "";
      return '<option value="' + html(value) + '" data-slug="' + html(clinic.slug || "") + '" data-id="' + html(clinic.id || "") + '"' + selected + '>' +
        html(clinicLabel(clinic)) + '</option>';
    }));
    select.innerHTML = options.join("");
  }

  function setMode(mode) {
    var isClaim = mode !== "recommend";
    show(el("claimForm"), isClaim);
    show(el("recommendForm"), !isClaim);
    [el("claimTab"), el("recommendTab")].forEach(function (button) {
      if (!button) return;
      var active = button.getAttribute("data-mode") === (isClaim ? "claim" : "recommend");
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", active ? "true" : "false");
    });
    setMessage("intakeMessage", "");
  }

  function setBusy(form, busy) {
    if (!form) return;
    Array.prototype.forEach.call(form.querySelectorAll("button, input, select, textarea"), function (node) {
      node.disabled = busy;
    });
  }

  function requireClient(messageId) {
    if (client) return true;
    setMessage(messageId, "La conexión segura aún no está activa.", "error");
    return false;
  }

  async function submitClaim(event) {
    event.preventDefault();
    if (!requireClient("intakeMessage")) return;
    var form = event.currentTarget;
    var clinic = selectedClinic("claimClinic");
    if (!clinic) {
      setMessage("intakeMessage", "Selecciona la clínica que quieres reclamar.", "error");
      return;
    }
    setBusy(form, true);
    setMessage("intakeMessage", "Enviando solicitud...");
    var result = await client.rpc("portal_submit_clinic_claim_request", {
      p_request_kind: "claim_existing",
      p_clinic_id: asUuid(clinic.id),
      p_clinic_slug: clinic.slug || null,
      p_clinic_name: clinic.name || null,
      p_clinic_website: clinic.web || null,
      p_clinic_city: clinic.city || null,
      p_clinic_country: clinic.country || null,
      p_contact_email: trimmed("claimEmail"),
      p_requester_name: trimmed("claimRequesterName"),
      p_requester_role: trimmed("claimRequesterRole") || null,
      p_message: trimmed("claimMessage") || null,
      p_source_urls: [],
      p_accept_manual_review: el("claimAccept").checked
    });
    setBusy(form, false);
    if (result.error) {
      setMessage("intakeMessage", result.error.message || "No se pudo enviar la solicitud.", "error");
      return;
    }
    form.reset();
    populateClaimClinics();
    setMessage("intakeMessage", "Solicitud recibida. Queda pendiente de validación manual.", "success");
  }

  async function submitRecommendation(event) {
    event.preventDefault();
    if (!requireClient("intakeMessage")) return;
    var form = event.currentTarget;
    setBusy(form, true);
    setMessage("intakeMessage", "Enviando recomendación...");
    var result = await client.rpc("portal_submit_clinic_claim_request", {
      p_request_kind: "recommend_clinic",
      p_clinic_id: null,
      p_clinic_slug: null,
      p_clinic_name: trimmed("recommendClinicName"),
      p_clinic_website: trimmed("recommendWebsite"),
      p_clinic_city: trimmed("recommendCity"),
      p_clinic_country: trimmed("recommendCountry") || "España",
      p_contact_email: trimmed("recommendEmail"),
      p_requester_name: trimmed("recommendRequesterName"),
      p_requester_role: trimmed("recommendRequesterRole") || null,
      p_message: trimmed("recommendMessage") || null,
      p_source_urls: validUrlsFromTextarea("recommendSourceUrls"),
      p_accept_manual_review: el("recommendAccept").checked
    });
    setBusy(form, false);
    if (result.error) {
      setMessage("intakeMessage", result.error.message || "No se pudo enviar la recomendación.", "error");
      return;
    }
    form.reset();
    el("recommendCountry").value = "España";
    setMessage("intakeMessage", "Recomendación recibida. Vitalarga la revisará antes de crear una ficha.", "success");
  }

  async function login(event) {
    event.preventDefault();
    if (!requireClient("loginMessage")) return;
    var email = trimmed("portalEmail");
    if (!email) {
      setMessage("loginMessage", "Introduce tu email.", "error");
      return;
    }
    setBusy(event.currentTarget, true);
    setMessage("loginMessage", "Preparando enlace de acceso...");
    var result = await client.auth.signInWithOtp({
      email: email,
      options: { emailRedirectTo: window.location.origin + "/portal-clinicas/" }
    });
    setBusy(event.currentTarget, false);
    if (result.error) {
      setMessage("loginMessage", result.error.message || "No se pudo enviar el enlace.", "error");
      return;
    }
    setMessage("loginMessage", "Enlace enviado. Revisa el email y vuelve por el enlace seguro.", "success");
  }

  function clinicCurrentValue(clinic, key) {
    var current = clinic.current_data || {};
    var topLevel = {
      display_name: clinic.display_name || current.name,
      website: clinic.website || current.web,
      city: clinic.city || current.city,
      country: clinic.country || current.country,
      region: clinic.region || current.region,
      address: clinic.address || current.address,
      summary: clinic.summary || current.summary
    };
    if (Object.prototype.hasOwnProperty.call(topLevel, key)) return topLevel[key] || "";
    return current[key];
  }

  function fillChangeForm() {
    var membership = selectedMembership();
    var clinic = membership && membership.clinic ? membership.clinic : {};
    el("changeDisplayName").value = clinicCurrentValue(clinic, "display_name") || "";
    el("changeWebsite").value = clinicCurrentValue(clinic, "website") || "";
    el("changeCity").value = clinicCurrentValue(clinic, "city") || "";
    el("changeCountry").value = clinicCurrentValue(clinic, "country") || "";
    el("changeRegion").value = clinicCurrentValue(clinic, "region") || "";
    el("changeAddress").value = clinicCurrentValue(clinic, "address") || "";
    el("changeSummary").value = clinicCurrentValue(clinic, "summary") || "";
    el("changeServices").value = arrayToLines(clinicCurrentValue(clinic, "services"));
    el("changeSpecialties").value = arrayToLines(clinicCurrentValue(clinic, "specialties"));
    el("changeUnits").value = arrayToLines(clinicCurrentValue(clinic, "unidades"));
    el("changeProfessionals").value = arrayToLines(clinicCurrentValue(clinic, "profesionales"));
    el("changeTech").value = arrayToLines(clinicCurrentValue(clinic, "tech"));
    el("changeEmail").value = clinicCurrentValue(clinic, "email") || "";
    el("changePhone").value = clinicCurrentValue(clinic, "telefono") || "";
    el("changeInstagram").value = clinicCurrentValue(clinic, "instagram") || "";
  }

  function proposedFieldsFromForm() {
    var membership = selectedMembership();
    var clinic = membership && membership.clinic ? membership.clinic : {};
    var fields = {};
    [
      ["display_name", "changeDisplayName"],
      ["website", "changeWebsite"],
      ["city", "changeCity"],
      ["country", "changeCountry"],
      ["region", "changeRegion"],
      ["address", "changeAddress"],
      ["summary", "changeSummary"],
      ["tech", "changeTech"],
      ["email", "changeEmail"],
      ["telefono", "changePhone"],
      ["instagram", "changeInstagram"]
    ].forEach(function (pair) {
      var key = pair[0];
      var value = trimmed(pair[1]);
      if (value && !sameValue(clinicCurrentValue(clinic, key), value)) fields[key] = value;
    });
    [
      ["services", "changeServices"],
      ["specialties", "changeSpecialties"],
      ["unidades", "changeUnits"],
      ["profesionales", "changeProfessionals"]
    ].forEach(function (pair) {
      var key = pair[0];
      var value = splitLines(trimmed(pair[1]));
      if (value.length && !sameValue(clinicCurrentValue(clinic, key), value)) fields[key] = value;
    });
    return fields;
  }

  async function submitChangeRequest(event) {
    event.preventDefault();
    if (!requireClient("workspaceMessage")) return;
    var membership = selectedMembership();
    if (!membership || !membership.clinic) {
      setMessage("workspaceMessage", "No hay una clínica aprobada seleccionada.", "error");
      return;
    }
    var proposedFields = proposedFieldsFromForm();
    if (!Object.keys(proposedFields).length) {
      setMessage("workspaceMessage", "Cambia al menos un campo antes de enviar.", "error");
      return;
    }
    setBusy(event.currentTarget, true);
    setMessage("workspaceMessage", "Enviando cambios para validar...");
    var result = await client.rpc("portal_submit_profile_change_request", {
      p_clinic_id: membership.clinic.id,
      p_proposed_fields: proposedFields,
      p_source_urls: validUrlsFromTextarea("changeSourceUrls"),
      p_message: trimmed("changeMessage") || null
    });
    setBusy(event.currentTarget, false);
    if (result.error) {
      setMessage("workspaceMessage", result.error.message || "No se pudieron enviar los cambios.", "error");
      return;
    }
    el("changeSourceUrls").value = "";
    el("changeMessage").value = "";
    setMessage("workspaceMessage", "Cambios enviados. Vitalarga los revisará antes de publicar.", "success");
    await loadWorkspace();
  }

  function renderMemberships() {
    var list = el("membershipList");
    var memberships = workspace.memberships || [];
    if (!memberships.length) {
      list.innerHTML = '<p class="empty-copy">Todavía no hay clínicas aprobadas para este email.</p>';
      return;
    }
    list.innerHTML = memberships.map(function (membership) {
      var clinic = membership.clinic || {};
      return '<article class="stack-item"><strong>' + html(clinic.display_name || "Clínica") + '</strong>' +
        '<small>' + html([clinic.city, clinic.country].filter(Boolean).join(" · ")) + '</small>' +
        '<span class="status-pill active">' + html(statusLabel(membership.status)) + '</span></article>';
    }).join("");
  }

  function renderRequests() {
    var list = el("requestList");
    var claimRequests = (workspace.claim_requests || []).map(function (request) {
      return {
        title: request.request_kind === "recommend_clinic" ? "Recomendación: " + request.clinic_name : "Reclamación: " + request.clinic_name,
        status: request.status,
        created_at: request.created_at,
        note: request.resolution_note || ""
      };
    });
    var changeRequests = (workspace.change_requests || []).map(function (request) {
      return {
        title: "Cambios: " + request.clinic_name,
        status: request.status,
        created_at: request.created_at,
        note: request.resolution_note || ""
      };
    });
    var requests = claimRequests.concat(changeRequests).sort(function (a, b) {
      return new Date(b.created_at || 0) - new Date(a.created_at || 0);
    }).slice(0, 8);
    if (!requests.length) {
      list.innerHTML = '<p class="empty-copy">Las solicitudes aparecerán aquí cuando existan.</p>';
      return;
    }
    list.innerHTML = requests.map(function (request) {
      return '<article class="stack-item"><strong>' + html(request.title) + '</strong>' +
        '<small>' + html(formatDate(request.created_at)) + (request.note ? " · " + html(request.note) : "") + '</small>' +
        '<span class="status-pill">' + html(statusLabel(request.status)) + '</span></article>';
    }).join("");
  }

  function populateChangeClinics() {
    var select = el("changeClinic");
    var memberships = workspace.memberships || [];
    select.innerHTML = memberships.map(function (membership) {
      var clinic = membership.clinic || {};
      return '<option value="' + html(clinic.id || "") + '">' + html(clinic.display_name || "Clínica") + '</option>';
    }).join("");
    show(el("changeForm"), memberships.length > 0);
    if (memberships.length) fillChangeForm();
  }

  function renderWorkspace() {
    var memberships = workspace.memberships || [];
    show(el("workspacePanel"), Boolean(session));
    renderMemberships();
    renderRequests();
    populateChangeClinics();
    if (!memberships.length) {
      setMessage("workspaceMessage", "Cuando Vitalarga apruebe tu acceso, aquí podrás proponer cambios de ficha.");
    } else {
      setMessage("workspaceMessage", "");
    }
  }

  async function loadWorkspace() {
    if (!client || !session) return;
    setMessage("workspaceMessage", "Actualizando estado...");
    var result = await client.rpc("portal_my_clinic_workspace");
    if (result.error) {
      setMessage("workspaceMessage", result.error.message || "No se pudo cargar tu zona privada.", "error");
      return;
    }
    workspace = result.data || { memberships: [], claim_requests: [], change_requests: [] };
    renderWorkspace();
  }

  function updateSession(nextSession) {
    session = nextSession || null;
    var signedIn = Boolean(session && session.user);
    show(el("loginForm"), !signedIn);
    show(el("sessionBox"), signedIn);
    show(el("workspacePanel"), signedIn);
    el("sessionPill").textContent = signedIn ? "Sesión activa" : "Sin sesión";
    el("sessionPill").classList.toggle("active", signedIn);
    el("sessionEmail").textContent = signedIn ? session.user.email || "" : "";
    if (!signedIn) {
      workspace = { memberships: [], claim_requests: [], change_requests: [] };
      renderWorkspace();
    }
  }

  async function signOut() {
    if (!client) return;
    await client.auth.signOut();
    updateSession(null);
    setMessage("loginMessage", "Sesión cerrada.");
  }

  async function initSupabase() {
    var ready = Boolean(config.supabaseUrl && config.supabasePublishableKey && window.supabase);
    show(el("configNotice"), !ready);
    if (!ready) {
      return;
    }
    client = window.supabase.createClient(config.supabaseUrl, config.supabasePublishableKey);
    var sessionResult = await client.auth.getSession();
    updateSession(sessionResult.data ? sessionResult.data.session : null);
    client.auth.onAuthStateChange(function (_event, nextSession) {
      updateSession(nextSession);
      if (nextSession) loadWorkspace();
    });
    if (session) await loadWorkspace();
  }

  function bindEvents() {
    populateClaimClinics();
    el("claimTab").addEventListener("click", function () { setMode("claim"); });
    el("recommendTab").addEventListener("click", function () { setMode("recommend"); });
    el("claimForm").addEventListener("submit", submitClaim);
    el("recommendForm").addEventListener("submit", submitRecommendation);
    el("loginForm").addEventListener("submit", login);
    el("signOutBtn").addEventListener("click", signOut);
    el("refreshWorkspaceBtn").addEventListener("click", loadWorkspace);
    el("changeClinic").addEventListener("change", fillChangeForm);
    el("changeForm").addEventListener("submit", submitChangeRequest);
    var params = new URLSearchParams(window.location.search);
    if (params.get("mode") === "recommend") setMode("recommend");
  }

  bindEvents();
  initSupabase();
})();
