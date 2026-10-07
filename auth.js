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
        return (await post('/api/auth/login', { email, password })).user;
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

    async function listPostComments(postId) {
        return (await request(`/api/posts/${encodeURIComponent(postId)}/comments`)).comments;
    }

    async function createPostComment(postId, content) {
        return (await post(`/api/posts/${encodeURIComponent(postId)}/comments`, { content })).comment;
    }

    async function updateProfileAvatar(imageData) {
        return (await post('/api/profile/avatar', { image_data: imageData })).avatar_url;
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

    async function getAdminOverview() {
        return request('/api/admin/overview');
    }

    async function createAdminMission(mission) {
        return post('/api/admin/missions', mission);
    }

    async function getAdminUsers() {
        return (await request('/api/admin/users')).users;
    }

    async function createAdminUser(user) {
        return (await post('/api/admin/users', user)).user;
    }

    async function createAdminPost(payload) {
        return post('/api/admin/posts', payload);
    }

    async function deleteResource(path) {
        return request(path, { method: 'DELETE' });
    }

    window.CivicAuth = { register, login, getCurrentUser, logout };
    window.CivicApi = {
        listPosts,
        createPost,
        listPostComments,
        createPostComment,
        updateProfileAvatar,
        createAlert,
        updateBusinessName,
        getDashboard,
        getMissions,
        completeMission,
        updateDailyGoal,
        getAdminOverview,
        createAdminMission,
        createAdminPost,
        deleteAdminPost: postId => deleteResource(`/api/admin/posts/${encodeURIComponent(postId)}`),
        deleteAdminMission: missionId => deleteResource(`/api/admin/missions/${encodeURIComponent(missionId)}`),
        getAdminUsers,
        createAdminUser,
        updateAdminUserRole: (userId, role) => post(`/api/admin/users/${encodeURIComponent(userId)}/role`, { role }),
        updateAdminUserAvatar: (userId, avatarUrl) => post(`/api/admin/users/${encodeURIComponent(userId)}/avatar`, { avatar_url: avatarUrl }),
        updateAdminPostStatus: (postId, status) => post(`/api/admin/posts/${encodeURIComponent(postId)}/status`, { status })
    };
})();