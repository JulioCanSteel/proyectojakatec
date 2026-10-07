(() => {
    const views = {
        overview: 'Resumen',
        reports: 'Reportes comunitarios',
        map: 'Mapa operativo',
        missions: 'Misiones de la comunidad',
        publish: 'Crear publicación',
        users: 'Usuarios y permisos'
    };
    let overview = null;
    let trendChart = null;
    let categoryChart = null;
    let map = null;
    let reportHeat = null;
    let markerLayer = null;
    let selectedMapReport = null;
    let currentUser = null;

    const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, character => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    })[character]);

    function notify(message, type = 'success') {
        const notice = document.getElementById('notice');
        notice.textContent = message;
        notice.className = `notice ${type}`;
        notice.hidden = false;
        window.clearTimeout(notify.timeout);
        notify.timeout = window.setTimeout(() => { notice.hidden = true; }, 5000);
    }

    function showView(viewName) {
        if (!views[viewName]) return;
        if (viewName === 'users' && currentUser?.role !== 'admin') return;
        if (['missions', 'publish'].includes(viewName) && currentUser?.role !== 'admin') return;
        document.querySelectorAll('.view').forEach(view => {
            view.classList.toggle('active', view.id === `view-${viewName}`);
        });
        document.querySelectorAll('[data-view]').forEach(button => {
            const active = button.dataset.view === viewName;
            button.classList.toggle('active', active);
            if (active) button.setAttribute('aria-current', 'page');
            else button.removeAttribute('aria-current');
        });
        document.getElementById('currentSection').textContent = views[viewName];
        if (viewName === 'map') {
            requestAnimationFrame(() => {
                initializeMap();
                map.invalidateSize();
            });
        }
    }

    function formatDate(value) {
        if (!value) return 'Fecha no disponible';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return 'Fecha no disponible';
        return new Intl.DateTimeFormat('es-MX', {
            dateStyle: 'medium',
            timeStyle: 'short'
        }).format(date);
    }

    function readImageFile(file) {
        if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
            throw new Error('Selecciona una imagen JPG, PNG o WebP.');
        }
        if (file.size > 5 * 1024 * 1024) {
            throw new Error('La imagen debe pesar 5 MB o menos.');
        }
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.addEventListener('load', () => resolve(reader.result));
            reader.addEventListener('error', () => reject(new Error('No se pudo leer la imagen seleccionada.')));
            reader.readAsDataURL(file);
        });
    }

    function renderStats(stats) {
        document.getElementById('statUsers').textContent = stats.users.toLocaleString('es-MX');
        document.getElementById('statActiveUsers').textContent = `${stats.active_users_30d.toLocaleString('es-MX')} activas en 30 días`;
        document.getElementById('statReports').textContent = stats.reports.toLocaleString('es-MX');
        document.getElementById('statReportsToday').textContent = `${stats.reports_today.toLocaleString('es-MX')} nuevos hoy · ${stats.reports_week.toLocaleString('es-MX')} esta semana`;
        document.getElementById('statAlerts').textContent = stats.alerts.toLocaleString('es-MX');
        document.getElementById('statMissions').textContent = stats.missions.toLocaleString('es-MX');
        document.getElementById('reportNavCount').textContent = stats.reports.toLocaleString('es-MX');
    }

    function renderRecentReports(reports) {
        const target = document.getElementById('recentReports');
        const latest = reports.slice(0, 5);
        if (!latest.length) {
            target.innerHTML = '<div class="empty-state"><i class="bi bi-inbox"></i>Aún no hay reportes comunitarios.</div>';
            return;
        }
        target.innerHTML = latest.map(report => `
            <div class="recent-row">
                <span class="report-symbol"><i class="bi ${report.is_demo ? 'bi-bezier2' : 'bi-geo-alt'}"></i></span>
                <div>
                    <div class="recent-title">${escapeHtml(report.title)}</div>
                    <div class="recent-meta">${escapeHtml(report.category)} · ${escapeHtml(report.author)} · ${escapeHtml(formatDate(report.created_at))}</div>
                </div>
                <span class="status-pill ${report.is_demo ? 'demo' : report.status === 'Publicado' ? 'published' : ''}">${escapeHtml(report.is_demo ? 'DEMO' : report.status)}</span>
            </div>
        `).join('');
    }

    function renderUsers(users) {
        document.getElementById('userCount').textContent = users.length;
        const target = document.getElementById('usersList');
        if (!users.length) {
            target.innerHTML = '<div class="empty-state"><i class="bi bi-people"></i>No hay cuentas registradas.</div>';
            return;
        }
        target.innerHTML = users.map(user => {
            const initials = user.name.trim().slice(0, 1).toLocaleUpperCase('es-MX');
            const avatar = typeof user.avatar_url === 'string'
                && (user.avatar_url.startsWith('https://') || user.avatar_url.startsWith('/uploads/'))
                ? `<img class="user-avatar-image" src="${escapeHtml(user.avatar_url)}" alt="" referrerpolicy="no-referrer">`
                : `<span class="avatar user-avatar-fallback">${escapeHtml(initials)}</span>`;
            return `
                <article class="user-row" data-user-id="${user.id}">
                    ${avatar}
                    <div class="user-identity"><strong>${escapeHtml(user.name)}</strong><span>${escapeHtml(user.email)}</span><small>Alta ${escapeHtml(formatDate(user.created_at))}</small></div>
                    <div class="user-controls">
                        <label class="user-role-control"><span>Permiso</span><select class="form-select form-select-sm" data-user-role="${user.id}" ${user.id === currentUser.id ? 'disabled' : ''}>
                            <option value="user" ${user.role === 'user' ? 'selected' : ''}>Usuario</option>
                            <option value="moderator" ${user.role === 'moderator' ? 'selected' : ''}>Moderador</option>
                            <option value="admin" ${user.role === 'admin' ? 'selected' : ''}>Administrador</option>
                        </select></label>
                        <label class="avatar-url-control"><span>Foto de perfil (URL HTTPS)</span><input class="form-control form-control-sm" data-user-avatar="${user.id}" type="url" value="${escapeHtml(user.avatar_url || '')}" placeholder="https://..."></label>
                        <div class="user-actions">
                            ${user.id === currentUser.id ? '<span class="self-role-note">Tu cuenta de control total</span>' : `<button class="btn btn-outline-primary btn-sm" type="button" data-save-role="${user.id}">Guardar rol</button>`}
                            <button class="btn btn-outline-secondary btn-sm" type="button" data-save-avatar="${user.id}">Guardar foto</button>
                        </div>
                    </div>
                </article>`;
        }).join('');
    }

    function drawCharts(data) {
        const trendContext = document.getElementById('trendChart');
        const categoryContext = document.getElementById('categoryChart');
        if (trendChart) trendChart.destroy();
        if (categoryChart) categoryChart.destroy();
        trendChart = new Chart(trendContext, {
            type: 'bar',
            data: {
                labels: data.report_trend.map(day => new Intl.DateTimeFormat('es-MX', { weekday: 'short', day: 'numeric' }).format(new Date(`${day.date}T12:00:00`))),
                datasets: [{
                    label: 'Reportes',
                    data: data.report_trend.map(day => day.count),
                    backgroundColor: '#1557a6',
                    hoverBackgroundColor: '#f2ad28',
                    borderRadius: 6,
                    maxBarThickness: 34
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: '#8190a1', font: { size: 10 } } },
                    y: { beginAtZero: true, ticks: { precision: 0, color: '#8190a1', font: { size: 10 } }, grid: { color: '#edf1f5' } }
                }
            }
        });
        const categories = data.reports_by_category;
        categoryChart = new Chart(categoryContext, {
            type: 'doughnut',
            data: {
                labels: categories.length ? categories.map(item => item.category || 'General') : ['Sin reportes'],
                datasets: [{
                    data: categories.length ? categories.map(item => item.count) : [1],
                    backgroundColor: ['#1557a6', '#f2ad28', '#137456', '#7154a3', '#df7a48', '#57a0a4', '#91a4b8'],
                    borderColor: '#fff',
                    borderWidth: 3,
                    hoverOffset: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '67%',
                plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 7, padding: 14, color: '#607187', font: { size: 9 } } } }
            }
        });
    }

    function populateCategoryFilter(reports) {
        const select = document.getElementById('categoryFilter');
        const selected = select.value;
        const categories = [...new Set(reports.map(report => report.category).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'es'));
        select.innerHTML = '<option value="">Todas las categorías</option>' + categories
            .map(category => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`).join('');
        select.value = categories.includes(selected) ? selected : '';
    }

    function reportStatus(report) {
        if (report.is_demo) return '<span class="status-pill demo">DEMO · solo consulta</span>';
        const published = report.status === 'Publicado';
        return `<span class="status-pill ${published || report.status === 'Atendido' ? 'published' : report.status === 'Descartado' ? 'demo' : ''}">${escapeHtml(report.status || 'Pendiente')}</span>`;
    }

    function renderReports() {
        const search = document.getElementById('reportSearch').value.trim().toLocaleLowerCase('es-MX');
        const category = document.getElementById('categoryFilter').value;
        const filtered = overview.reports.filter(report => {
            const content = `${report.title} ${report.description} ${report.author} ${report.email}`.toLocaleLowerCase('es-MX');
            return (!search || content.includes(search)) && (!category || report.category === category);
        });
        document.getElementById('reportResultCount').textContent = `${filtered.length} ${filtered.length === 1 ? 'reporte' : 'reportes'}`;
        const target = document.getElementById('reportsList');
        if (!filtered.length) {
            target.innerHTML = '<div class="empty-state"><i class="bi bi-search"></i>No hay reportes que coincidan con los filtros.</div>';
            return;
        }
        target.innerHTML = filtered.map(report => `
            <article class="panel-card report-card">
                <span class="report-symbol"><i class="bi ${report.is_demo ? 'bi-bezier2' : 'bi-geo-alt'}"></i></span>
                <div class="report-body">
                    <div class="report-title-row"><h2 class="report-title">${escapeHtml(report.title)}</h2>${reportStatus(report)}</div>
                    <p class="report-description">${escapeHtml(report.description)}</p>
                    ${typeof report.image_url === 'string' && (report.image_url.startsWith('/uploads/') || report.image_url.startsWith('https://')) ? `<img class="admin-report-image" src="${escapeHtml(report.image_url)}" alt="Foto adjunta al reporte" loading="lazy">` : ''}
                    ${report.is_demo ? '' : `<label class="report-status-control">Estado <select data-report-status="${report.id}" class="form-select form-select-sm">${['Pendiente', 'En revisión', 'Atendido', 'Descartado'].map(status => `<option value="${status}" ${report.status === status ? 'selected' : ''}>${status}</option>`).join('')}</select></label>`}
                    <div class="report-meta">
                        <span><i class="bi bi-tag"></i>${escapeHtml(report.category)}</span>
                        <span><i class="bi bi-person"></i>${escapeHtml(report.author)}${report.email ? ` · ${escapeHtml(report.email)}` : ''}</span>
                        <span><i class="bi bi-clock"></i>${escapeHtml(formatDate(report.created_at))}</span>
                        ${Number.isFinite(report.latitude) && Number.isFinite(report.longitude) ? `<span><i class="bi bi-pin-map"></i>${Number(report.latitude).toFixed(4)}, ${Number(report.longitude).toFixed(4)}</span>` : '<span><i class="bi bi-pin-map"></i>Sin ubicación</span>'}
                    </div>
                </div>
                ${report.is_demo || currentUser?.role !== 'admin' ? '' : `<div class="report-actions"><button class="btn-delete" type="button" data-delete-report="${escapeHtml(report.id)}" aria-label="Eliminar ${escapeHtml(report.title)}"><i class="bi bi-trash3 me-1"></i>Eliminar</button></div>`}
            </article>
        `).join('');
    }

    function renderCommunityPosts(posts) {
        document.getElementById('communityPostCount').textContent = posts.length;
        const target = document.getElementById('adminPostsList');
        if (!posts.length) {
            target.innerHTML = '<div class="empty-state"><i class="bi bi-chat-square-text"></i>Aún no hay publicaciones sociales.</div>';
            return;
        }
        target.innerHTML = posts.map(post => `
            <article class="admin-community-post" data-admin-post="${post.id}">
                <div class="admin-community-post-copy">
                    <strong>${escapeHtml(post.title)}</strong>
                    <span>${escapeHtml(post.author)} · ${escapeHtml(formatDate(post.created_at))}</span>
                    <p>${escapeHtml(post.description)}</p>
                    ${typeof post.image_url === 'string' && (post.image_url.startsWith('/uploads/') || post.image_url.startsWith('https://')) ? `<img class="admin-report-image" src="${escapeHtml(post.image_url)}" alt="Foto de la publicación" loading="lazy">` : ''}
                </div>
                <button class="btn-delete" type="button" data-delete-community-post="${escapeHtml(post.id)}" aria-label="Eliminar ${escapeHtml(post.title)}"><i class="bi bi-trash3 me-1"></i>Eliminar</button>
            </article>
        `).join('');
    }

    function renderMissions(missions) {
        document.getElementById('missionCount').textContent = missions.length;
        const target = document.getElementById('missionsList');
        if (!missions.length) {
            target.innerHTML = '<div class="empty-state"><i class="bi bi-trophy"></i>Aún no se han creado misiones. Usa el formulario para publicar la primera.</div>';
            return;
        }
        target.innerHTML = missions.map(mission => `
            <div class="mission-row">
                <span class="mission-icon"><i class="bi ${escapeHtml(mission.icon)}"></i></span>
                <div class="mission-copy"><strong>${escapeHtml(mission.title)}</strong><p>${escapeHtml(mission.description)}</p><span class="mission-reward">+${mission.points} pts · +${mission.coins} monedas</span></div>
                <button class="btn-delete" type="button" data-delete-mission="${mission.id}" aria-label="Eliminar misión ${escapeHtml(mission.title)}"><i class="bi bi-trash3"></i></button>
            </div>
        `).join('');
    }

    function renderAlerts(alerts) {
        const target = document.getElementById('alertsList');
        if (!alerts.length) {
            target.innerHTML = '<div class="empty-state"><i class="bi bi-bell-slash"></i>Aún no hay alertas registradas.</div>';
            return;
        }
        target.innerHTML = alerts.slice(0, 10).map(alert => `
            <div class="recent-row">
                <span class="report-symbol alert-symbol"><i class="bi bi-bell-fill"></i></span>
                <div>
                    <div class="recent-title">Alerta ${escapeHtml(alert.alert_type === 'voice' ? 'por voz' : 'manual')}</div>
                    <div class="recent-meta">${escapeHtml(alert.author)} · ${escapeHtml(alert.email)} · ${escapeHtml(formatDate(alert.created_at))}</div>
                </div>
                <span class="status-pill ${Number.isFinite(alert.latitude) && Number.isFinite(alert.longitude) ? 'published' : ''}">${Number.isFinite(alert.latitude) && Number.isFinite(alert.longitude) ? `${Number(alert.latitude).toFixed(3)}, ${Number(alert.longitude).toFixed(3)}` : 'Sin ubicación'}</span>
            </div>
        `).join('');
    }

    function selectMapReport(report) {
        selectedMapReport = report;
        const target = document.getElementById('mapInspector');
        if (report.is_alert) {
            target.innerHTML = `
                <div class="inspector-kicker"><i class="bi bi-bell-fill"></i> Alerta de seguridad</div>
                <h2>${escapeHtml(report.alert_type === 'voice' ? 'Alerta por voz' : 'Alerta manual')}</h2>
                <div class="inspector-details">
                    <div><span>Persona</span><strong>${escapeHtml(report.author)}</strong></div>
                    <div><span>Correo</span><strong>${escapeHtml(report.email)}</strong></div>
                    <div><span>Fecha</span><strong>${escapeHtml(formatDate(report.created_at))}</strong></div>
                    <div><span>Ubicación</span><strong>${Number(report.latitude).toFixed(5)}, ${Number(report.longitude).toFixed(5)}</strong></div>
                </div>
                <div class="inspector-caution"><i class="bi bi-info-circle"></i> La app registra alertas en el servidor; no contacta al 911 ni a servicios de emergencia.</div>`;
            return;
        }
        target.innerHTML = `
            <div class="inspector-kicker"><i class="bi bi-geo-alt-fill"></i> ${report.is_demo ? 'Reporte de demostración' : 'Reporte comunitario'}</div>
            <h2>${escapeHtml(report.title)}</h2>
            <p class="inspector-description">${escapeHtml(report.description)}</p>
            ${typeof report.image_url === 'string' && (report.image_url.startsWith('/uploads/') || report.image_url.startsWith('https://')) ? `<img class="admin-report-image" src="${escapeHtml(report.image_url)}" alt="Foto adjunta al reporte" loading="lazy">` : ''}
            <div class="inspector-details">
                <div><span>Categoría</span><strong>${escapeHtml(report.category)}</strong></div>
                <div><span>Reportado por</span><strong>${escapeHtml(report.author)}</strong></div>
                <div><span>Fecha</span><strong>${escapeHtml(formatDate(report.created_at))}</strong></div>
                <div><span>Coordenadas</span><strong>${Number(report.latitude).toFixed(5)}, ${Number(report.longitude).toFixed(5)}</strong></div>
            </div>
            ${report.is_demo ? '<div class="inspector-caution"><i class="bi bi-info-circle"></i> Dato sintético: no representa un incidente real.</div>' : `
                <label class="form-label mt-3" for="mapStatusSelect">Estado del reporte</label>
                <select id="mapStatusSelect" class="form-select">${['Pendiente', 'En revisión', 'Atendido', 'Descartado'].map(status => `<option value="${status}" ${report.status === status ? 'selected' : ''}>${status}</option>`).join('')}</select>
                <button class="btn btn-primary w-100 mt-2" id="saveMapStatus" type="button"><i class="bi bi-check2 me-2"></i>Guardar estado</button>`}`;
        const saveButton = document.getElementById('saveMapStatus');
        if (saveButton) {
            saveButton.addEventListener('click', async () => {
                const status = document.getElementById('mapStatusSelect').value;
                saveButton.disabled = true;
                try {
                    await window.CivicApi.updateAdminPostStatus(report.id, status);
                    await loadOverview();
                    const refreshed = overview.reports.find(item => String(item.id) === String(report.id));
                    if (refreshed) selectMapReport(refreshed);
                    notify('Estado del reporte actualizado.');
                } catch (error) {
                    notify(error.message || 'No se pudo cambiar el estado.', 'error');
                    saveButton.disabled = false;
                }
            });
        }
    }

    function initializeMap() {
        if (!map) {
            map = L.map('adminMap', { scrollWheelZoom: false }).setView([23.6345, -102.5528], 5);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 18,
                attribution: '&copy; OpenStreetMap contributors'
            }).addTo(map);
            reportHeat = L.heatLayer([], {
                radius: 32,
                blur: 24,
                maxZoom: 12,
                max: 1,
                gradient: { 0.2: '#2c7bb6', 0.45: '#abd9e9', 0.65: '#ffffbf', 0.82: '#fdae61', 1: '#d7191c' }
            }).addTo(map);
            markerLayer = L.featureGroup().addTo(map);
        }
        reportHeat.setLatLngs([]);
        markerLayer.clearLayers();
        const reportLocations = overview.reports.filter(report =>
            report.kind === 'report' && Number.isFinite(report.latitude) && Number.isFinite(report.longitude)
        );
        const alertLocations = overview.alerts.filter(alert =>
            Number.isFinite(alert.latitude) && Number.isFinite(alert.longitude)
        );
        const locationCounts = new Map();
        reportLocations.forEach(report => {
            const key = `${report.latitude.toFixed(4)},${report.longitude.toFixed(4)}`;
            locationCounts.set(key, (locationCounts.get(key) || 0) + 1);
        });
        const maxLocationCount = Math.max(1, ...locationCounts.values());
        reportHeat.setLatLngs(reportLocations.map(report => {
            const key = `${report.latitude.toFixed(4)},${report.longitude.toFixed(4)}`;
            return [report.latitude, report.longitude, Math.max(.18, locationCounts.get(key) / maxLocationCount)];
        }));
        reportLocations.forEach(report => {
            const marker = L.circleMarker([report.latitude, report.longitude], {
                radius: report.is_demo ? 5 : 6,
                color: report.status === 'Atendido' ? '#137456' : report.status === 'Descartado' ? '#64748b' : '#104987',
                fillColor: report.status === 'Atendido' ? '#35a874' : report.status === 'Descartado' ? '#94a3b8' : '#1557a6',
                fillOpacity: .9,
                weight: 2,
                dashArray: report.is_demo ? '3 3' : undefined
            });
            marker.on('click', () => selectMapReport(report));
            markerLayer.addLayer(marker);
        });
        alertLocations.forEach(alert => {
            const marker = L.circleMarker([alert.latitude, alert.longitude], {
                radius: 7,
                color: '#b42332',
                fillColor: '#d94848',
                fillOpacity: .8,
                weight: 2
            });
            marker.on('click', () => selectMapReport({ ...alert, is_alert: true }));
            markerLayer.addLayer(marker);
        });
        if (markerLayer.getLayers().length) map.fitBounds(markerLayer.getBounds().pad(.15), { maxZoom: 12 });
        else map.setView([23.6345, -102.5528], 5);
        document.getElementById('mappedReports').textContent = reportLocations.length;
        document.getElementById('mappedAlerts').textContent = alertLocations.length;
        if (selectedMapReport && !selectedMapReport.is_alert) {
            const refreshed = overview.reports.find(report => String(report.id) === String(selectedMapReport.id));
            if (refreshed) selectMapReport(refreshed);
        }
    }

    async function loadOverview() {
        const data = await window.CivicApi.getAdminOverview();
        overview = data;
        renderStats(data.stats);
        drawCharts(data);
        renderRecentReports(data.reports);
        populateCategoryFilter(data.reports);
        renderReports();
        renderAlerts(data.alerts);
        renderMissions(data.missions);
        if (currentUser?.role === 'admin') {
            renderUsers(data.users || []);
            renderCommunityPosts(data.community_posts || []);
        }
        if (map) initializeMap();
    }

    async function initialize() {
        try {
            const user = await window.CivicAuth.getCurrentUser();
            if (!user) {
                window.location.replace('/login/loguin.html');
                return;
            }
            if (!['admin', 'moderator'].includes(user.role)) {
                notify('Tu cuenta no cuenta con permisos administrativos.', 'error');
                window.setTimeout(() => window.location.replace('/feed/index.html'), 1800);
                return;
            }
            currentUser = user;
            if (user.role !== 'admin') {
                document.querySelectorAll('.admin-only').forEach(element => { element.hidden = true; });
            }
            if (user.avatar_url) {
                const avatar = document.getElementById('adminAvatar');
                const image = document.createElement('img');
                image.src = user.avatar_url;
                image.alt = `Foto de perfil de ${user.name}`;
                image.referrerPolicy = 'no-referrer';
                image.addEventListener('error', () => image.remove(), { once: true });
                avatar.append(image);
            }
            document.getElementById('adminName').textContent = user.name;
            document.getElementById('adminInitials').textContent = user.name.trim().slice(0, 1).toLocaleUpperCase('es-MX');
            await loadOverview();
        } catch (error) {
            notify(error.message || 'No se pudo cargar el panel administrativo.', 'error');
        }
    }

    document.querySelectorAll('[data-view]').forEach(button => {
        button.addEventListener('click', () => showView(button.dataset.view));
    });
    document.querySelectorAll('[data-goto]').forEach(button => {
        button.addEventListener('click', () => showView(button.dataset.goto));
    });
    document.getElementById('refreshButton').addEventListener('click', async () => {
        try {
            await loadOverview();
            notify('Los datos del panel están actualizados.');
        } catch (error) {
            notify(error.message || 'No se pudo actualizar el panel.', 'error');
        }
    });
    document.getElementById('reportSearch').addEventListener('input', renderReports);
    document.getElementById('categoryFilter').addEventListener('change', renderReports);
    document.getElementById('reportsList').addEventListener('change', async event => {
        const select = event.target.closest('[data-report-status]');
        if (!select) return;
        try {
            await window.CivicApi.updateAdminPostStatus(select.dataset.reportStatus, select.value);
            const report = overview.reports.find(item => String(item.id) === String(select.dataset.reportStatus));
            if (report) report.status = select.value;
            renderRecentReports(overview.reports);
            if (map) initializeMap();
            notify('Estado del reporte actualizado.');
        } catch (error) {
            notify(error.message || 'No se pudo cambiar el estado.', 'error');
            renderReports();
        }
    });
    document.getElementById('reportsList').addEventListener('click', async event => {
        const button = event.target.closest('[data-delete-report]');
        if (!button || !window.confirm('¿Eliminar esta publicación definitivamente?')) return;
        try {
            await window.CivicApi.deleteAdminPost(button.dataset.deleteReport);
            await loadOverview();
            notify('La publicación fue eliminada.');
        } catch (error) {
            notify(error.message || 'No se pudo eliminar la publicación.', 'error');
        }
    });
    document.getElementById('adminPostsList').addEventListener('click', async event => {
        const button = event.target.closest('[data-delete-community-post]');
        if (!button || !window.confirm('¿Eliminar esta publicación de la comunidad?')) return;
        try {
            await window.CivicApi.deleteAdminPost(button.dataset.deleteCommunityPost);
            await loadOverview();
            notify('La publicación fue eliminada del feed.');
        } catch (error) {
            notify(error.message || 'No se pudo eliminar la publicación.', 'error');
        }
    });
    document.getElementById('usersList').addEventListener('click', async event => {
        const roleButton = event.target.closest('[data-save-role]');
        const avatarButton = event.target.closest('[data-save-avatar]');
        if (!roleButton && !avatarButton) return;
        const button = roleButton || avatarButton;
        const userId = button.dataset.saveRole || button.dataset.saveAvatar;
        try {
            if (roleButton) {
                const role = document.querySelector(`[data-user-role="${userId}"]`).value;
                await window.CivicApi.updateAdminUserRole(userId, role);
                await loadOverview();
                notify('Permiso actualizado.');
            } else {
                const avatarUrl = document.querySelector(`[data-user-avatar="${userId}"]`).value.trim();
                await window.CivicApi.updateAdminUserAvatar(userId, avatarUrl);
                await loadOverview();
                notify('Foto de perfil actualizada.');
            }
        } catch (error) {
            notify(error.message || 'No se pudo actualizar la cuenta.', 'error');
        }
    });
    document.getElementById('staffForm').addEventListener('submit', async event => {
        event.preventDefault();
        const form = event.currentTarget;
        const staff = {
            name: document.getElementById('staffName').value.trim(),
            email: document.getElementById('staffEmail').value.trim(),
            password: document.getElementById('staffPassword').value,
            role: document.getElementById('staffRole').value,
            avatar_url: document.getElementById('staffAvatar').value.trim()
        };
        try {
            await window.CivicApi.createAdminUser(staff);
            form.reset();
            await loadOverview();
            notify('Cuenta de personal creada; ya puede iniciar sesión.');
        } catch (error) {
            notify(error.message || 'No se pudo crear la cuenta de personal.', 'error');
        }
    });
    document.getElementById('missionsList').addEventListener('click', async event => {
        const button = event.target.closest('[data-delete-mission]');
        if (!button || !window.confirm('¿Eliminar esta misión de la comunidad?')) return;
        try {
            await window.CivicApi.deleteAdminMission(button.dataset.deleteMission);
            await loadOverview();
            notify('La misión fue eliminada.');
        } catch (error) {
            notify(error.message || 'No se pudo eliminar la misión.', 'error');
        }
    });
    document.getElementById('missionForm').addEventListener('submit', async event => {
        event.preventDefault();
        const form = event.currentTarget;
        const mission = {
            title: document.getElementById('missionTitle').value.trim(),
            description: document.getElementById('missionDescription').value.trim(),
            points: Number(document.getElementById('missionPoints').value),
            coins: Number(document.getElementById('missionCoins').value),
            icon: document.getElementById('missionIcon').value
        };
        try {
            await window.CivicApi.createAdminMission(mission);
            form.reset();
            document.getElementById('missionPoints').value = '10';
            document.getElementById('missionCoins').value = '10';
            await loadOverview();
            notify('Misión publicada. Ya está disponible en Misiones para la comunidad.');
        } catch (error) {
            notify(error.message || 'No se pudo publicar la misión.', 'error');
        }
    });
    document.getElementById('postImage').addEventListener('change', async event => {
        const input = event.currentTarget;
        const file = input.files[0];
        const preview = document.getElementById('postImagePreview');
        if (!file) {
            preview.hidden = true;
            preview.removeAttribute('src');
            return;
        }
        try {
            preview.src = await readImageFile(file);
            preview.hidden = false;
        } catch (error) {
            input.value = '';
            preview.hidden = true;
            notify(error.message, 'error');
        }
    });
    document.getElementById('publishForm').addEventListener('submit', async event => {
        event.preventDefault();
        const form = event.currentTarget;
        const imageFile = document.getElementById('postImage').files[0];
        const post = {
            title: document.getElementById('postTitle').value.trim(),
            description: document.getElementById('postDescription').value.trim(),
            category: document.getElementById('postCategory').value,
            anonymous: false,
            image_data: ''
        };
        try {
            post.image_data = imageFile ? await readImageFile(imageFile) : '';
            await window.CivicApi.createAdminPost(post);
            form.reset();
            document.getElementById('postImagePreview').hidden = true;
            document.getElementById('postImagePreview').removeAttribute('src');
            await loadOverview();
            notify('La publicación ya está visible en el feed de la comunidad.');
            showView('reports');
        } catch (error) {
            notify(error.message || 'No se pudo publicar el aviso.', 'error');
        }
    });
    document.getElementById('logoutButton').addEventListener('click', async () => {
        try {
            await window.CivicAuth.logout();
            window.location.replace('/login/loguin.html');
        } catch (error) {
            notify(error.message || 'No se pudo cerrar la sesión.', 'error');
        }
    });

    initialize();
})();
