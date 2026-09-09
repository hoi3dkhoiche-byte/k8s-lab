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
        
        const headers = {
            'Content-Type': 'application/json',
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
                throw new Error(data.message || 'Có lỗi xảy ra');
            }
            
            return data;
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    },

    cart: {
        items: JSON.parse(localStorage.getItem('cart')) || [],
        
        getCart() {
            return Promise.resolve({ items: this.items });
        },
        
        addToCart(productId, quantity = 1, productData = null) {
            const existing = this.items.find(i => i.id === productId);
            if (existing) {
                existing.quantity += quantity;
            } else if (productData) {
                this.items.push({ ...productData, id: productId, quantity });
            } else {
                this.items.push({ id: productId, quantity, name: 'Sản phẩm ' + productId, price: 1000000 });
            }
            localStorage.setItem('cart', JSON.stringify(this.items));
            return Promise.resolve({ success: true, items: this.items });
        },
        
        updateQuantity(productId, quantity) {
            const item = this.items.find(i => i.id === productId);
            if (item) {
                item.quantity = quantity;
                localStorage.setItem('cart', JSON.stringify(this.items));
            }
            return Promise.resolve({ success: true, items: this.items });
        },
        
        removeItem(productId) {
            this.items = this.items.filter(i => i.id !== productId);
            localStorage.setItem('cart', JSON.stringify(this.items));
            return Promise.resolve({ success: true, items: this.items });
        },
        
        clear() {
            this.items = [];
            localStorage.removeItem('cart');
            return Promise.resolve({ success: true });
        }
    },
    
    auth: {
        login(username, password) {
            return new Promise((resolve, reject) => {
                setTimeout(() => {
                    if (username && password) {
                        const token = 'mock_jwt_token_' + Date.now();
                        Api.setToken(token);
                        sessionStorage.setItem('user', JSON.stringify({ username, name: 'Người dùng Bida' }));
                        resolve({ token, user: { username } });
                    } else {
                        reject(new Error('Sai tài khoản hoặc mật khẩu'));
                    }
                }, 500);
            });
        },
        logout() {
            Api.removeToken();
            sessionStorage.removeItem('user');
        }
    },

    catalog: {
        productsList: [
            // Gậy Pool (Cues)
            { 
                id: 1, 
                name: 'Gậy Predator REVO 12.4 SP2', 
                price: 25500000, 
                category: 'cues', 
                categoryName: 'Gậy Pool Cao Cấp',
                img: 'images/cue-predator-revo.jpg',
                desc: 'Predator REVO 12.4 SP2 là dòng gậy thi đấu đỉnh cao kết hợp chuôi gỗ Maple chọn lọc với ngọn carbon fiber siêu nhẹ. Công nghệ triệt tiêu độ lệch (low deflection) hàng đầu giúp cơ thủ thực hiện các cú ép phê chuẩn xác tuyệt đối.',
                stock: true,
                specs: { 'Thương hiệu': 'Predator (Mỹ)', 'Công nghệ ngọn': 'Carbon Fiber REVO 12.4mm', 'Khớp nối': 'Uni-Loc Quick Release', 'Đầu cơ': 'Predator Victory Soft', 'Trọng lượng': '19oz (có thể tinh chỉnh)' }
            },
            { 
                id: 4, 
                name: 'Gậy Cuetec Cynergy 15K Truewood', 
                price: 18500000, 
                category: 'cues', 
                categoryName: 'Gậy Pool Cao Cấp',
                img: 'images/cue-cuetec-cynergy.jpg',
                desc: 'Gậy Cuetec Cynergy 15K Truewood mang đến cảm giác đánh tự nhiên và êm ái nhờ công nghệ ngọn carbon composite sợi đa hướng. Phù hợp cho cả cơ thủ bán chuyên và thi đấu chuyên nghiệp.',
                stock: true,
                specs: { 'Thương hiệu': 'Cuetec', 'Công nghệ ngọn': 'Cynergy 15K Carbon 12.5mm', 'Khớp nối': '3/8x14 Joint Pin', 'Đầu cơ': 'Tiger Sniper', 'Trọng lượng': '19oz' }
            },
            { 
                id: 7, 
                name: 'Gậy Lucasi Custom LZC Exotic', 
                price: 12500000, 
                category: 'cues', 
                categoryName: 'Gậy Pool Cao Cấp',
                img: 'images/cue-lucasi-custom.jpg',
                desc: 'Được chế tác từ gỗ Cocobolo quý hiếm kết hợp khảm hoa văn tinh xảo phong cách cổ điển. Đem lại độ đầm tay hoàn hảo trong từng đường cơ.',
                stock: true,
                specs: { 'Thương hiệu': 'Lucasi Custom', 'Chất liệu': 'Gỗ Cocobolo & Curly Maple', 'Khớp nối': 'Uni-Loc', 'Đầu cơ': 'Kamui Black Soft', 'Trọng lượng': '19.5oz' }
            },
            { 
                id: 9, 
                name: 'Gậy Mezz AXI-152 Japan', 
                price: 16800000, 
                category: 'cues', 
                categoryName: 'Gậy Pool Cao Cấp',
                img: 'images/cue-mezz-axi.jpg',
                desc: 'Sản xuất trực tiếp tại Nhật Bản với độ tinh xảo cơ khí cao. Trang bị khớp nối Wavy Joint danh tiếng của Mezz cho cảm giác tiếp xúc bi cực kỳ chân thực.',
                stock: true,
                specs: { 'Thương hiệu': 'Mezz Cues (Nhật Bản)', 'Ngọn đi kèm': 'WX700 Maple Shaft', 'Khớp nối': 'Wavy Joint', 'Tay cầm': 'Bọc chỉ Ailen cao cấp', 'Trọng lượng': '19.2oz' }
            },
            { 
                id: 10, 
                name: 'Gậy McDermott G-Core Classic', 
                price: 9500000, 
                category: 'cues', 
                categoryName: 'Gậy Pool Cao Cấp',
                img: 'images/cue-mcdermott.jpg',
                desc: 'Dòng cơ truyền thống sản xuất tại Wisconsin, Mỹ. Sử dụng lõi Carbon Tenon ở phần đầu ngọn giúp trợ lực và tăng độ kiểm soát bi cái.',
                stock: true,
                specs: { 'Thương hiệu': 'McDermott (Mỹ)', 'Ngọn': 'G-Core High-Performance', 'Khớp nối': '3/8x10', 'Đầu cơ': 'Navigator Black', 'Trọng lượng': '19oz' }
            },
            { 
                id: 11, 
                name: 'Gậy J.Pechauer Pro Series Limited', 
                price: 21000000, 
                category: 'cues', 
                categoryName: 'Gậy Pool Cao Cấp',
                img: 'images/cue-pechauer.jpg',
                desc: 'Phiên bản giới hạn thủ công mỹ nghệ. Cán gậy ghép từ gỗ Birdseye Maple và đá ngọc lam, tôn vinh đẳng cấp thượng lưu cho chủ sở hữu.',
                stock: true,
                specs: { 'Thương hiệu': 'J.Pechauer', 'Dòng': 'Custom Limited Edition', 'Khớp nối': 'Pechauer Speed Joint', 'Đầu cơ': 'Pechauer Gold Tip', 'Trọng lượng': '19.3oz' }
            },
            
            // Phụ Kiện (Accessories) - Ngọn, Tẩy, Lơ, Găng tay
            { 
                id: 2, 
                name: 'Ngọn Mezz WX-Sigma Shaft', 
                price: 8900000, 
                category: 'accessories', 
                categoryName: 'Phụ Kiện Chuyên Nghiệp',
                img: 'images/shaft-mezz-wx.jpg',
                desc: 'Ngọn WX-Sigma thế hệ mới của Mezz với độ văng thấp, cấu trúc gỗ sấy đặc biệt tối ưu hoá năng lượng truyền vào bi cái.',
                stock: true,
                specs: { 'Đường kính ngọn': '12.5mm', 'Khớp ren': 'United hoặc Wavy Joint', 'Phíp': 'XTC Ferrule', 'Đầu tẩy': 'Kamui Original S' }
            },
            { 
                id: 14, 
                name: 'Ngọn Carbon Predator REVO 11.8mm', 
                price: 11500000, 
                category: 'accessories', 
                categoryName: 'Phụ Kiện Chuyên Nghiệp',
                img: 'images/shaft-carbon-revo.jpg',
                desc: 'Ngọn carbon mỏng 11.8mm dành cho cơ thủ thích kiểm soát xoáy sâu, rút bi và điều bi với độ chính xác mi-li-mét.',
                stock: true,
                specs: { 'Chất liệu': 'Aerospace Carbon Fiber', 'Đường kính': '11.8mm', 'Khớp': 'Uni-Loc / Radial', 'Đầu tẩy': 'Predator Victory Soft' }
            },
            { 
                id: 5, 
                name: 'Lơ Bida Kamui Roku Chalk (Chính hãng)', 
                price: 650000, 
                category: 'accessories', 
                categoryName: 'Phụ Kiện Chuyên Nghiệp',
                img: 'images/chalk-kamui-roku.jpg',
                desc: 'Lơ lục giác Kamui Roku danh tiếng Nhật Bản, bám bi cực bền, chống tẹt cơ tối đa, không để lại bụi bẩn trên mặt bàn vải nỉ.',
                stock: true,
                specs: { 'Xuất xứ': 'Nhật Bản', 'Quy cách': 'Viên lục giác', 'Màu sắc': 'Sky Blue', 'Độ bám': 'Siêu bám dính' }
            },
            { 
                id: 6, 
                name: 'Đầu Tẩy Cơ Zan Plus2 Premium Tip', 
                price: 450000, 
                category: 'accessories', 
                categoryName: 'Phụ Kiện Chuyên Nghiệp',
                img: 'images/tip-zan-plus2.jpg',
                desc: 'Được làm từ 9 lớp da lợn chất lượng cao ép đặc biệt, giữ form đầu cơ lâu dài không bị bẹt hay chai cứng.',
                stock: true,
                specs: { 'Xuất xứ': 'Nhật Bản', 'Độ cứng': 'Medium (M) / Soft (S)', 'Số lớp da': '9 lớp ép nhiệt', 'Kích thước': '14mm' }
            },
            { 
                id: 12, 
                name: 'Đầu Tẩy Predator Victory 8 Lớp', 
                price: 550000, 
                category: 'accessories', 
                categoryName: 'Phụ Kiện Chuyên Nghiệp',
                img: 'images/tip-predator-victory.jpg',
                desc: 'Đầu cơ 8 lớp màu vàng đặc trưng của Predator, duy trì độ nén ổn định suốt tuổi thọ sử dụng.',
                stock: true,
                specs: { 'Thương hiệu': 'Predator', 'Độ cứng': 'Soft / Medium / Hard', 'Đường kính': '14mm' }
            },
            { 
                id: 13, 
                name: 'Găng Tay Predator Second Skin Pro', 
                price: 850000, 
                category: 'accessories', 
                categoryName: 'Phụ Kiện Chuyên Nghiệp',
                img: 'images/glove-predator.jpg',
                desc: 'Chất liệu vải co giãn thoáng khí siêu mịn, chống mồ hôi tay tuyệt đối, cho những cú vuốt ngọn trơn tru hoàn hảo.',
                stock: true,
                specs: { 'Chất liệu': 'Lycra siêu mịn thoáng khí', 'Màu': 'Đen - Vàng Gold', 'Kích cỡ': 'S/M và L/XL', 'Loại tay': 'Tay trái / Tay phải' }
            },
            
            // Bao & Hộp (Cases)
            { 
                id: 3, 
                name: 'Bao Đựng Gậy 3x4 Predator Urbain', 
                price: 4500000, 
                category: 'cases', 
                categoryName: 'Bao & Hộp Gậy Cao Cấp',
                img: 'images/case-predator-urbain.jpg',
                desc: 'Thiết kế phong cách thời trang đô thị, chứa được 3 chuôi 4 ngọn, lót nhung chống sốc và chống ẩm cực tốt.',
                stock: true,
                specs: { 'Sức chứa': '3 Chuôi - 4 Ngọn (3x4)', 'Chất liệu': 'Vải dệt chống nước & Da PU cao cấp', 'Ngăn phụ': 'Ngăn chứa lơ, khăn, phụ kiện rộng rãi', 'Dây đeo': 'Đệm êm công thái học' }
            },
            { 
                id: 8, 
                name: 'Hộp Gậy Da JB Cases 2x4 Custom', 
                price: 7200000, 
                category: 'cases', 
                categoryName: 'Bao & Hộp Gậy Cao Cấp',
                img: 'images/case-jb-custom.jpg',
                desc: 'Thương hiệu bao gậy bảo vệ số 1 thế giới. Khung cứng bên trong chịu lực đè nén cực cao, bọc da thủ công tinh xảo.',
                stock: true,
                specs: { 'Sức chứa': '2 Chuôi - 4 Ngọn (2x4)', 'Vỏ ngoài': 'Da thuộc tự nhiên dập nổi', 'Lõi bảo vệ': 'UltraPad chống sốc độc quyền JB' }
            },
            { 
                id: 15, 
                name: 'Bao Gậy Thể Thao Mezz MZ-35 Compact', 
                price: 3200000, 
                category: 'cases', 
                categoryName: 'Bao & Hộp Gậy Cao Cấp',
                img: 'images/case-mezz-mz35.jpg',
                desc: 'Dòng bao gậy gọn nhẹ cho cơ thủ thường xuyên di chuyển. Đạt tiêu chuẩn chất lượng khắt khe từ hãng Mezz Nhật Bản.',
                stock: true,
                specs: { 'Sức chứa': '3 Chuôi - 5 Ngọn (3x5)', 'Chất liệu': 'Nylon Ballistic chống rách', 'Trọng lượng': '1.4kg' }
            },
            { 
                id: 16, 
                name: 'Hộp Vali Gậy Lucasi Luxury Hard Case', 
                price: 5500000, 
                category: 'cases', 
                categoryName: 'Bao & Hộp Gậy Cao Cấp',
                img: 'images/case-lucasi-hard.jpg',
                desc: 'Hộp vali cứng có khóa số bảo mật an toàn khi đi máy bay. Nội thất lót nỉ nhung cao cấp ngăn ngừa trầy xước.',
                stock: true,
                specs: { 'Sức chứa': '4 Chuôi - 8 Ngọn (4x8)', 'Khóa': 'Khóa số kim loại mạ crom', 'Chất liệu': 'Khung nhôm bọc da vân cá sấu' }
            }
        ],

        async getProducts(params = {}) {
            let filtered = [...this.productsList];
            if (params.category && params.category !== 'all') {
                filtered = filtered.filter(p => p.category === params.category);
            }
            if (params.search) {
                const s = params.search.toLowerCase();
                filtered = filtered.filter(p => p.name.toLowerCase().includes(s) || (p.desc && p.desc.toLowerCase().includes(s)));
            }
            return Promise.resolve({ items: filtered });
        },

        async getProduct(id) {
            const numId = parseInt(id, 10);
            const found = this.productsList.find(p => p.id === numId) || this.productsList[0];
            return Promise.resolve(found);
        }
    }
};
