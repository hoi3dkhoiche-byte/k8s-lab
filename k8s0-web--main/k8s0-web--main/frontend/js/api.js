const Api = {
    baseUrl: '/api',
    
    getToken() {
        return sessionStorage.getItem('token');
    },
    
    setToken(token) {
        sessionStorage.setItem('token', token);
    },
    
    removeToken() {
        sessionStorage.removeItem('token');
    },

    async fetchWithAuth(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const token = this.getToken();
        
        const isFormData = options.body instanceof FormData;
        const headers = {
            ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
            ...(options.headers || {})
        };
        
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        
        const config = {
            ...options,
            headers
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                if (response.status === 401) {
                    this.removeToken();
                    sessionStorage.removeItem('user');
                }
                throw new Error(data.detail || data.message || 'Có lỗi xảy ra');
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    cart: {
        async getCart() {
            return Api.fetchWithAuth('/cart/');
        },
        
        async addToCart(productId, quantity = 1, productData = null) {
            return Api.fetchWithAuth('/cart/add', {
                method: 'POST',
                body: JSON.stringify({ product_id: String(productId), quantity })
            });
        },
        
        async updateQuantity(productId, quantity) {
            return Api.fetchWithAuth('/cart/update', {
                method: 'PUT',
                body: JSON.stringify({ product_id: String(productId), quantity })
            });
        },
        
        async removeItem(productId) {
            return Api.fetchWithAuth(`/cart/remove/${productId}`, {
                method: 'DELETE'
            });
        },
        
        async clear() {
            return Api.fetchWithAuth('/cart/clear', {
                method: 'DELETE'
            });
        }
    },
    
    auth: {
        async login(username, password) {
            const data = await Api.fetchWithAuth('/auth/login', {
                method: 'POST',
                body: JSON.stringify({ username, password })
            });
            Api.setToken(data.access_token);
            // Use user from login response directly, fallback to /me
            const user = data.user || await this.getMe();
            sessionStorage.setItem('user', JSON.stringify(user));
            return { token: data.access_token, user };
        },

        async register(username, email, password, fullName) {
            const data = await Api.fetchWithAuth('/auth/register', {
                method: 'POST',
                body: JSON.stringify({ username, email, password, full_name: fullName })
            });
            if (data.access_token) {
                Api.setToken(data.access_token);
                const user = await this.getMe();
                sessionStorage.setItem('user', JSON.stringify(user));
            }
            return data;
        },

        async getMe() {
            return Api.fetchWithAuth('/auth/me');
        },

        getUser() {
            try {
                const userStr = sessionStorage.getItem('user');
                return userStr ? JSON.parse(userStr) : null;
            } catch (e) {
                return null;
            }
        },

        isAdmin() {
            const user = this.getUser();
            return !!(user && user.role === 'admin');
        },

        logout() {
            Api.removeToken();
            sessionStorage.removeItem('user');
        }
    },

    catalog: {
        async getProducts(params = {}) {
            const query = new URLSearchParams();
            if (params.category && params.category !== 'all') {
                query.append('category', params.category);
            }
            if (params.search) {
                query.append('search', params.search);
            }
            if (params.page) {
                query.append('page', params.page);
            }
            if (params.limit) {
                query.append('limit', params.limit);
            }
            if (params.featured !== undefined) {
                query.append('featured', params.featured);
            }
            
            const qs = query.toString();
            return Api.fetchWithAuth(`/catalog/products${qs ? '?' + qs : ''}`);
        },

        async getProduct(id) {
            return Api.fetchWithAuth(`/catalog/products/${id}`);
        },

        async createProduct(productData) {
            return Api.fetchWithAuth('/catalog/products', {
                method: 'POST',
                body: JSON.stringify(productData)
            });
        },

        async updateProduct(id, productData) {
            return Api.fetchWithAuth(`/catalog/products/${id}`, {
                method: 'PUT',
                body: JSON.stringify(productData)
            });
        },

        async deleteProduct(id) {
            return Api.fetchWithAuth(`/catalog/products/${id}`, {
                method: 'DELETE'
            });
        },

        async uploadImage(file) {
            const formData = new FormData();
            formData.append('file', file);
            return Api.fetchWithAuth('/catalog/products/upload-image', {
                method: 'POST',
                body: formData
            });
        }
    },

    order: {
        async create(orderData) {
            return Api.fetchWithAuth('/orders/', {
                method: 'POST',
                body: JSON.stringify(orderData)
            });
        },

        async checkout(paymentData) {
            return Api.fetchWithAuth('/payments/checkout', {
                method: 'POST',
                body: JSON.stringify(paymentData)
            });
        },

        async getMyOrders() {
            return Api.fetchWithAuth('/orders/');
        },

        async getAllOrders() {
            return Api.fetchWithAuth('/orders/all');
        },

        async cancelOrder(orderId) {
            return Api.fetchWithAuth(`/orders/${orderId}/cancel`, {
                method: 'PUT'
            });
        },

        async updateStatus(orderId, status) {
            return Api.fetchWithAuth(`/orders/${orderId}/status`, {
                method: 'PUT',
                body: JSON.stringify({ status })
            });
        }
    }
};
