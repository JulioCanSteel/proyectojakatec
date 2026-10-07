(() => {
    if (window.location.protocol === 'file:') {
        const routes = [
            '/signup/signup.html',
            '/login/loguin.html',
            '/feed/index.html',
            '/perfil/perfil.html',
            '/seguridad/index.html'
        ];
        const route = routes.find(candidate => window.location.pathname.endsWith(candidate));
        if (route) {
            window.location.replace(`http://localhost:8000${route}`);
            return;
        }
    }

    async function request(path, options = {}) {
        let response;
        try {
            response = await fetch(path, {
                ...options,
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });
        } catch {
            throw new Error('No se pudo conectar con el servidor. Abre la aplicación desde el puerto 8000.');
        }
        const result = await response.json().catch(() => ({}));

        if (!response.ok) {
            const error = new Error(result.error || 'No se pudo completar la solicitud.');
            error.status = response.status;
            throw error;
        }

        return result;
    }

    function post(path, payload = {}) {
        return request(path, { method: 'POST', body: JSON.stringify(payload) });
    }

    async function register(name, email, password) {
        await post('/api/auth/register', { name, email, password });
    }

    async function login(email, password) {
        await post('/api/auth/login', { email, password });
    }

    async function getCurrentUser() {
        try {
            return (await request('/api/auth/me')).user;
        } catch (error) {
            if (error.status === 401) {
                return null;
            }
            throw error;
        }
    }

    async function logout() {
        await post('/api/auth/logout');
    }

    async function listPosts() {
        return (await request('/api/posts')).posts;
    }

    async function createPost(title, description, details = {}) {
        return (await post('/api/posts', { title, description, ...details })).post;
    }

    async function createAlert(type, position = null) {
        return (await post('/api/alerts', { type, ...position })).alert;
    }

    async function updateBusinessName(businessName) {
        return (await post('/api/profile/business', { business_name: businessName })).business_name;
    }

    async function getDashboard() {
        return request('/api/dashboard');
    }

    async function getMissions() {
        return (await request('/api/missions')).missions;
    }

    async function completeMission(missionId) {
        return post('/api/missions/complete', { mission_id: missionId });
    }

    async function updateDailyGoal(dailyGoal) {
        return post('/api/profile/goal', { daily_goal: dailyGoal });
    }

    window.CivicAuth = { register, login, getCurrentUser, logout };
    window.CivicApi = {
        listPosts,
        createPost,
        createAlert,
        updateBusinessName,
        getDashboard,
        getMissions,
        completeMission,
        updateDailyGoal
    };
})();