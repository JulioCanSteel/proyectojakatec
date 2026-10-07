(() => {
    const sections = [
        { id: 'home', label: 'Inicio', icon: 'bi-house', path: '/feed/index.html' },
        { id: 'security', label: 'Seguridad', icon: 'bi-shield-check', path: '/seguridad/index.html' },
        { id: 'services', label: 'Trámites', icon: 'bi-building', path: '/gov/gov.html' },
        { id: 'missions', label: 'Misiones', icon: 'bi-trophy', path: '/missions/missions.html' },
        { id: 'progress', label: 'Progreso', icon: 'bi-bar-chart', path: '/mi_progreso/mi_progreso.html' },
        { id: 'profile', label: 'Perfil', icon: 'bi-person', path: '/perfil/perfil.html' }
    ];

    function renderNavigation() {
        const nav = document.querySelector('.bottom-menu');
        if (!nav) return;
        const pathname = window.location.pathname;
        const current = sections.find(section => pathname.endsWith(section.path))?.id;
        nav.setAttribute('aria-label', 'Secciones principales');
        nav.replaceChildren(...sections.map(section => {
            const link = document.createElement('a');
            link.href = section.path;
            link.className = section.id === current ? 'active' : '';
            if (section.id === current) link.setAttribute('aria-current', 'page');
            const icon = document.createElement('i');
            icon.className = `bi ${section.icon}`;
            const label = document.createElement('span');
            label.textContent = section.label;
            link.append(icon, label);
            return link;
        }));
    }

    document.addEventListener('DOMContentLoaded', async () => {
        renderNavigation();
        if (!window.CivicAuth) return;

        try {
            const user = await window.CivicAuth.getCurrentUser();
            if (!user) {
                window.location.replace('/login/loguin.html');
                return;
            }
            document.querySelectorAll('[data-user-name]').forEach(element => {
                element.textContent = user.name;
            });
        } catch (error) {
            console.error('No se pudo validar la sesión.', error);
        }
    });

    window.CivicApp = {
        async loadDashboard() {
            const dashboard = await window.CivicApi.getDashboard();
            const { stats, streak, user } = dashboard;
            const values = {
                headerCoins: stats.coins,
                headerStreak: streak.days,
                streakDays: streak.days,
                statRacha: streak.days,
                statAportes: stats.contributions,
                statCompletadas: stats.missions_completed,
                statSemana: stats.weekly_points,
                statGanancias: stats.coins,
                statLogros: dashboard.achievements.length,
                userName: user.name,
                userLevel: `Nivel ${stats.level}`,
                welcomeName: `¡Hola, ${user.name}!`,
                welcomeLevel: `Nivel ${stats.level}`
            };

            Object.entries(values).forEach(([id, value]) => {
                const element = document.getElementById(id);
                if (element) element.textContent = value;
            });

            const barValues = {
                barAportesValue: [stats.contributions, 10],
                barLogrosValue: [dashboard.achievements.length, 5],
                barLevelValue: [stats.level, 10]
            };
            Object.entries(barValues).forEach(([id, [value, target]]) => {
                const label = document.getElementById(id);
                if (label) label.textContent = value;
                const bar = document.getElementById(id.replace('Value', ''));
                if (bar) bar.style.width = `${Math.min(100, Math.round(value / target * 100))}%`;
            });

            document.querySelectorAll('[data-dashboard="coins"]').forEach(element => {
                element.textContent = stats.coins;
            });
            document.querySelectorAll('[data-dashboard="streak"]').forEach(element => {
                element.textContent = streak.days;
            });
            return dashboard;
        },

        renderWeek(container, week) {
            if (!container) return;
            container.replaceChildren(...week.map(day => {
                const item = document.createElement('div');
                item.className = `mx-1 font-space day-box ${day.active ? 'day-completed' : 'day-pending'}`;
                item.textContent = day.label;
                item.title = day.date;
                return item;
            }));
        },

        showMessage(message) {
            const status = document.querySelector('[data-app-status]');
            if (status) status.textContent = message;
            else window.alert(message);
        }
    };
})();