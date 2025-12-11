// Alpine.js App State and Main Application Logic

function app() {
    return {
        // Authentication State
        isAuthenticated: false,
        authMode: 'login',
        authError: '',
        currentUser: {},
        usersOnline: 0,
        
        // Login/Register Forms
        loginForm: {
            username: '',
            password: '',
            remember: true  // Default to true for better UX
        },
        registerForm: {
            username: '',
            password: '',
            major: '',
            graduation_year: null,
            remember: true  // Default to true for better UX
        },
        
        // View State
        currentView: 'home',
        
        // User Stats
        studyStreak: 0,
        totalQuestions: 0,
        accuracy: 0,
        topicsStudied: 0,
        weeklyQuestions: 0,
        masteredTopics: 0,
        dailyProgress: 0,
        xpProgress: {},
        
        // Quiz State
        currentQuestion: null,
        allTopics: [],
        guideMeSteps: [],
        currentGuideMeStep: 0,
        showGuideMeModal: false,
        
        // Leaderboards
        leaderboardType: 'global',
        leaderboardPeriod: 'alltime',
        leaderboardData: [],
        myRank: null,
        totalUsers: 0,
        
        // Achievements
        allAchievements: [],
        
        // Documents
        documents: [],
        
        // Exam Questions
        exams: [],
        selectedExamQuestions: null, // null = not loaded, [] = loaded but empty
        examUploadForm: {
            examName: ''
        },
        
        // Charts
        forgettingCurveChart: null,
        masteryProgressChart: null,
        timeOfDayChart: null,
        topicDistributionChart: null,
        
        // Initialize app
        async init() {
            // Check authentication
            await this.checkAuth();
            
            // Initialize MathJax lazy loading
            this.initMathJaxLazyLoading();
            
            if (this.isAuthenticated) {
                this.loadStats();
                this.initCharts();
                this.setupEventListeners();
                this.loadSocialProof();
                this.loadAchievements();
                this.loadDocuments();
                this.loadExams();
                
                // Load activity feed
                this.loadActivityFeed();
                
                // Poll for updates every 60 seconds
                setInterval(() => {
                    this.loadSocialProof();
                    this.loadActivityFeed();
                    if (this.currentView === 'leaderboards') {
                        this.loadLeaderboard();
                    }
                }, 60000);
                
                // Watch for view changes
                this.$watch('currentView', (newView) => {
                    if (newView === 'leaderboards') {
                        this.loadLeaderboard();
                    } else if (newView === 'achievements') {
                        this.loadAchievements();
                    } else if (newView === 'documents') {
                        this.loadDocuments();
                    } else if (newView === 'exam-questions') {
                        this.loadExams();
                    }
                });
            } else {
                // Load social proof for login screen
                this.loadSocialProof();
            }
        },
        
        async checkAuth() {
            try {
                const response = await fetch('/auth/me');
                if (response.ok) {
                    const data = await response.json();
                    this.isAuthenticated = true;
                    this.currentUser = data.user;
                    this.usersOnline = data.users_online;
                    this.xpProgress = data.xp_progress || {};
                    this.studyStreak = data.user.study_streak || 0;
                } else {
                    this.isAuthenticated = false;
                }
            } catch (err) {
                this.isAuthenticated = false;
            }
        },
        
        async login() {
            this.authError = '';
            try {
                const response = await fetch('/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(this.loginForm)
                });
                const data = await response.json();
                
                if (response.ok) {
                    this.isAuthenticated = true;
                    this.currentUser = data.user;
                    await this.init();
                } else {
                    this.authError = data.error || 'Login failed';
                }
            } catch (err) {
                this.authError = 'Connection error';
            }
        },
        
        async register() {
            this.authError = '';
            try {
                const response = await fetch('/auth/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(this.registerForm)
                });
                const data = await response.json();
                
                if (response.ok) {
                    this.isAuthenticated = true;
                    this.currentUser = data.user;
                    await this.init();
                } else {
                    this.authError = data.error || 'Registration failed';
                }
            } catch (err) {
                this.authError = 'Connection error';
            }
        },
        
        async logout() {
            try {
                await fetch('/auth/logout', {method: 'POST'});
                this.isAuthenticated = false;
                this.currentUser = {};
                this.currentView = 'home';
            } catch (err) {
                console.error('Logout error:', err);
            }
        },
        
        async loginWithGoogle() {
            this.authError = '';
            
            try {
                // Wait for Google Identity Services to load
                await new Promise((resolve) => {
                    if (typeof google !== 'undefined' && google.accounts) {
                        resolve();
                    } else {
                        const checkInterval = setInterval(() => {
                            if (typeof google !== 'undefined' && google.accounts) {
                                clearInterval(checkInterval);
                                resolve();
                            }
                        }, 100);
                        
                        // Timeout after 5 seconds
                        setTimeout(() => {
                            clearInterval(checkInterval);
                            resolve();
                        }, 5000);
                    }
                });
                
                if (typeof google === 'undefined' || !google.accounts) {
                    this.authError = 'Google Sign In not loaded. Please refresh the page.';
                    return;
                }
                
                // Get Google Client ID from environment or use a placeholder
                const clientId = await this.getGoogleClientId();
                
                if (!clientId || clientId === 'YOUR_GOOGLE_CLIENT_ID') {
                    this.authError = 'Google Sign In not configured. Please contact support or use username/password.';
                    return;
                }
                
                // Initialize Google Sign In
                google.accounts.id.initialize({
                    client_id: clientId,
                    callback: async (response) => {
                        try {
                            // Send credential to backend
                            const authResponse = await fetch('/auth/google', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({
                                    credential: response.credential
                                })
                            });
                            
                            const data = await authResponse.json();
                            
                            if (authResponse.ok) {
                                this.isAuthenticated = true;
                                this.currentUser = data.user;
                                await this.init();
                            } else {
                                this.authError = data.error || 'Google login failed';
                            }
                        } catch (err) {
                            console.error('Google login error:', err);
                            this.authError = 'Error processing Google login';
                        }
                    }
                });
                
                // Trigger sign in popup
                google.accounts.id.prompt((notification) => {
                    if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
                        // Fallback: show one tap
                        google.accounts.id.renderButton(
                            document.getElementById('google-signin-button'),
                            { theme: 'outline', size: 'large' }
                        );
                    }
                });
                
            } catch (err) {
                console.error('Google OAuth error:', err);
                this.authError = 'Google Sign In error. Please try again or use username/password.';
            }
        },
        
        async getGoogleClientId() {
            // Try to get from backend config
            try {
                const response = await fetch('/auth/config');
                const data = await response.json();
                return data.google_client_id;
            } catch (err) {
                // Return placeholder - in production, this should be set in Railway env vars
                return null;
            }
        },
        
        
        async loadSocialProof() {
            try {
                const response = await fetch('/social-proof');
                const data = await response.json();
                this.usersOnline = data.active_now || 0;
            } catch (err) {
                console.error('Error loading social proof:', err);
            }
        },
        
        loadStats() {
            fetch('/stats')
                .then(response => response.json())
                .then(data => {
                    this.updateStatsFromData(data);
                })
                .catch(err => console.error('Error loading stats:', err));
            
            // Load analytics
            this.loadAnalytics();
        },
        
        updateStatsFromData(data) {
            if (!data.user_state) return;
            
            const userState = data.user_state;
            let totalAttempts = 0;
            let totalCorrect = 0;
            let topicsCount = 0;
            let mastered = 0;
            
            for (const [topicId, stats] of Object.entries(userState)) {
                totalAttempts += stats.attempts || 0;
                totalCorrect += stats.correct || 0;
                topicsCount++;
                if (stats.mastery > 0.8) mastered++;
            }
            
            this.totalQuestions = totalAttempts;
            this.accuracy = totalAttempts > 0 ? Math.round((totalCorrect / totalAttempts) * 100) : 0;
            this.topicsStudied = topicsCount;
            this.masteredTopics = mastered;
            
            // Update right panel stats
            this.updateRightPanelStats(userState);
        },
        
        loadAnalytics() {
            fetch('/analytics')
                .then(response => response.json())
                .then(data => {
                    if (!data.error) {
                        this.studyStreak = data.study_streak || 0;
                        this.updatePerformanceInsights(data);
                        this.updateWeakTopics(data.weak_topics || []);
                    }
                })
                .catch(err => console.error('Error loading analytics:', err));
        },
        
        updatePerformanceInsights(data) {
            const container = document.getElementById('performance-insights');
            if (!container) return;
            
            container.innerHTML = `
                <p class="flex items-start space-x-2">
                    <span>🔥</span>
                    <span>Current study streak: ${data.study_streak || 0} days</span>
                </p>
                <p class="flex items-start space-x-2">
                    <span>💪</span>
                    <span>Strong topics: ${(data.strong_topics || []).length} topics with 80%+ mastery</span>
                </p>
                <p class="flex items-start space-x-2">
                    <span>⚠️</span>
                    <span>Topics needing practice: ${(data.weak_topics || []).length}</span>
                </p>
            `;
        },
        
        updateWeakTopics(weakTopics) {
            const container = document.getElementById('weak-topics-list');
            if (!container) return;
            
            if (weakTopics.length === 0) {
                container.innerHTML = '<p class="text-slate-400 text-xs">Great job! No weak topics.</p>';
                return;
            }
            
            container.innerHTML = weakTopics.slice(0, 3).map(topic => `
                <div class="flex justify-between items-center p-2 bg-slate-600 rounded">
                    <span class="text-xs truncate flex-1">${topic.topic_id}</span>
                    <span class="text-xs text-yellow-400">${Math.round(topic.mastery * 100)}%</span>
                </div>
            `).join('');
        },
        
        updateRightPanelStats(userState) {
            // Update upcoming reviews
            const reviewsContainer = document.getElementById('upcoming-reviews-list');
            if (reviewsContainer) {
                const reviewsNeeded = [];
                const now = new Date();
                
                for (const [topicId, stats] of Object.entries(userState)) {
                    if (stats.next_review) {
                        const nextReview = new Date(stats.next_review);
                        if (nextReview <= now || (nextReview - now) < 24 * 60 * 60 * 1000) {
                            reviewsNeeded.push({ topicId, nextReview });
                        }
                    }
                }
                
                if (reviewsNeeded.length === 0) {
                    reviewsContainer.innerHTML = '<p class="text-slate-400 text-xs">No reviews due soon!</p>';
                } else {
                    reviewsContainer.innerHTML = reviewsNeeded.slice(0, 5).map(item => `
                        <div class="flex justify-between items-center text-xs">
                            <span class="truncate flex-1">${item.topicId}</span>
                            <span class="text-blue-400">Due</span>
                        </div>
                    `).join('');
                }
            }
        },
        
        initCharts() {
            // Will be populated when analytics view is loaded
            setTimeout(() => {
                if (this.currentView === 'analytics') {
                    this.loadForgettingCurveData();
                    this.loadMasteryProgressData();
                    this.loadTimeOfDayData();
                    this.loadTopicDistributionData();
                    this.generateStudyHeatmap();
                }
            }, 500);
        },
        
        loadForgettingCurveData() {
            fetch('/forgetting-curve-data')
                .then(response => response.json())
                .then(data => {
                    this.renderForgettingCurveChart(data);
                })
                .catch(err => console.error('Error loading forgetting curve:', err));
        },
        
        renderForgettingCurveChart(data) {
            const ctx = document.getElementById('forgettingCurveChart');
            if (!ctx) return;
            
            if (this.forgettingCurveChart) {
                this.forgettingCurveChart.destroy();
            }
            
            const datasets = data.topics?.map((topic, idx) => {
                const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
                const color = colors[idx % colors.length];
                
                return {
                    label: topic.name,
                    data: topic.retention_data,
                    borderColor: color,
                    backgroundColor: color + '20',
                    tension: 0.4,
                    fill: false
                };
            }) || [];
            
            this.forgettingCurveChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Now', '1d', '2d', '3d', '5d', '7d', '14d', '30d'],
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            labels: { color: '#f1f5f9', font: { size: 11 } }
                        },
                        tooltip: {
                            callbacks: {
                                label: (context) => `${context.dataset.label}: ${context.parsed.y.toFixed(1)}%`
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            grid: { color: '#334155' },
                            ticks: {
                                color: '#94a3b8',
                                callback: (value) => value + '%'
                            }
                        },
                        x: {
                            grid: { color: '#334155' },
                            ticks: { color: '#94a3b8' }
                        }
                    }
                }
            });
        },
        
        loadMasteryProgressData() {
            fetch('/performance-dashboard')
                .then(response => response.json())
                .then(data => {
                    this.renderMasteryProgressChart(data.mastery_over_time || {});
                })
                .catch(err => console.error('Error loading mastery progress:', err));
        },
        
        renderMasteryProgressChart(data) {
            const ctx = document.getElementById('masteryProgressChart');
            if (!ctx) return;
            
            if (this.masteryProgressChart) {
                this.masteryProgressChart.destroy();
            }
            
            // Sample data if none provided
            const labels = data.labels || ['Week 1', 'Week 2', 'Week 3', 'Week 4'];
            const datasets = data.datasets || [{
                label: 'Average Mastery',
                data: [0, 45, 60, 75],
                borderColor: '#3b82f6',
                backgroundColor: '#3b82f620',
                tension: 0.4,
                fill: true
            }];
            
            this.masteryProgressChart = new Chart(ctx, {
                type: 'line',
                data: { labels, datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            labels: { color: '#f1f5f9', font: { size: 11 } }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            grid: { color: '#334155' },
                            ticks: {
                                color: '#94a3b8',
                                callback: (value) => value + '%'
                            }
                        },
                        x: {
                            grid: { color: '#334155' },
                            ticks: { color: '#94a3b8' }
                        }
                    }
                }
            });
        },
        
        loadTimeOfDayData() {
            fetch('/time-of-day-stats')
                .then(response => response.json())
                .then(data => {
                    this.renderTimeOfDayChart(data);
                })
                .catch(err => console.error('Error loading time of day stats:', err));
        },
        
        renderTimeOfDayChart(data) {
            const ctx = document.getElementById('timeOfDayChart');
            if (!ctx) return;
            
            if (this.timeOfDayChart) {
                this.timeOfDayChart.destroy();
            }
            
            const labels = data.labels || ['6-9 AM', '9-12 PM', '12-3 PM', '3-6 PM', '6-9 PM', '9 PM+'];
            const accuracyData = data.accuracy || [0, 0, 0, 0, 0, 0];
            
            this.timeOfDayChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels,
                    datasets: [{
                        label: 'Accuracy (%)',
                        data: accuracyData,
                        backgroundColor: '#3b82f6',
                        borderRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100,
                            grid: { color: '#334155' },
                            ticks: {
                                color: '#94a3b8',
                                callback: (value) => value + '%'
                            }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { color: '#94a3b8' }
                        }
                    }
                }
            });
        },
        
        loadTopicDistributionData() {
            fetch('/performance-dashboard')
                .then(response => response.json())
                .then(data => {
                    this.renderTopicDistributionChart(data.topic_distribution || {});
                })
                .catch(err => console.error('Error loading topic distribution:', err));
        },
        
        renderTopicDistributionChart(data) {
            const ctx = document.getElementById('topicDistributionChart');
            if (!ctx) return;
            
            if (this.topicDistributionChart) {
                this.topicDistributionChart.destroy();
            }
            
            const labels = data.labels || [];
            const values = data.values || [];
            
            this.topicDistributionChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels,
                    datasets: [{
                        data: values,
                        backgroundColor: [
                            '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
                            '#06b6d4', '#ec4899', '#14b8a6'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: { color: '#f1f5f9', font: { size: 11 } }
                        }
                    }
                }
            });
        },
        
        generateStudyHeatmap() {
            const container = document.getElementById('studyHeatmap');
            if (!container) return;
            
            // Generate 8 weeks of data
            const weeks = 8;
            const days = 7;
            let html = '<div class="flex space-x-1">';
            
            for (let week = 0; week < weeks; week++) {
                html += '<div class="flex flex-col space-y-1">';
                for (let day = 0; day < days; day++) {
                    const intensity = Math.floor(Math.random() * 5);
                    html += `<div class="heatmap-cell intensity-${intensity}" title="Week ${week + 1}, Day ${day + 1}"></div>`;
                }
                html += '</div>';
            }
            html += '</div>';
            
            container.innerHTML = html;
        },
        
        setupEventListeners() {
            this.setupUploadForm();
            this.setupQuizButtons();
            // Guide Me now uses Alpine.js, no setup needed
            this.setupExamPrepForm();
            this.setupSettingsButtons();
        },
        
        setupUploadForm() {
            const form = document.getElementById('upload-form');
            if (!form) return;
            
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const fileInput = document.getElementById('file-input');
                const statusDiv = document.getElementById('upload-status');
                
                if (!fileInput.files.length) {
                    statusDiv.textContent = 'Please select a file';
                    return;
                }
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);
                
                statusDiv.textContent = 'Uploading and extracting topics...';
                
                try {
                    const response = await fetch('/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) {
                        const errorData = await response.json().catch(() => ({ error: 'Unknown error occurred' }));
                        statusDiv.textContent = 'Error: ' + (errorData.error || `Server error: ${response.status}`);
                        console.error('Upload error:', errorData);
                        return;
                    }
                    
                    const data = await response.json();
                    console.log('Upload response:', data); // Debug log
                    
                    if (data.error) {
                        statusDiv.textContent = 'Error: ' + data.error;
                        return;
                    }
                    
                    if (!data.topics || !Array.isArray(data.topics)) {
                        statusDiv.textContent = 'Error: Invalid response from server. Topics not found.';
                        console.error('Invalid topics data:', data);
                        console.error('Response status:', response.status);
                        console.error('Full response:', await response.clone().json());
                        return;
                    }
                    
                    statusDiv.textContent = 'Topics extracted successfully!';
                    this.allTopics = data.topics;
                    this.displayTopics(data.topics);
                    this.populateExamTopics(data.topics);
                    // Reload documents list
                    this.loadDocuments();
                } catch (err) {
                    statusDiv.textContent = 'Error: ' + err.message;
                }
            });
        },
        
        displayTopics(topics) {
            const topicsList = document.getElementById('topics-list');
            const section = document.getElementById('topics-section');
            
            if (!topicsList || !section) return;
            
            // Safety check
            if (!topics || !Array.isArray(topics) || topics.length === 0) {
                topicsList.innerHTML = '<li class="text-slate-400">No topics found</li>';
                section.style.display = 'block';
                return;
            }
            
            topicsList.innerHTML = '';
            
            topics.forEach((topic, index) => {
                const li = document.createElement('li');
                li.className = 'topic-item';
                
                const header = document.createElement('div');
                header.className = 'topic-header';
                
                const nameSpan = document.createElement('span');
                nameSpan.className = 'topic-name';
                nameSpan.textContent = topic.name;
                nameSpan.addEventListener('click', () => this.toggleExplanation(index));
                
                const testBtn = document.createElement('button');
                testBtn.className = 'test-topic-btn';
                testBtn.innerHTML = '📝 Practice';
                testBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    this.generateQuestionForTopic(topic.topic_id);
                });
                
                header.appendChild(nameSpan);
                header.appendChild(testBtn);
                
                const explanation = document.createElement('div');
                explanation.className = 'topic-explanation';
                explanation.id = `explanation-${index}`;
                explanation.textContent = topic.explanation || 'No explanation available.';
                explanation.style.display = 'none';
                
                li.appendChild(header);
                li.appendChild(explanation);
                topicsList.appendChild(li);
            });
            
            section.style.display = 'block';
        },
        
        toggleExplanation(index) {
            const explanation = document.getElementById(`explanation-${index}`);
            if (explanation) {
                explanation.style.display = explanation.style.display === 'none' ? 'block' : 'none';
            }
        },
        
        setupQuizButtons() {
            const startBtn = document.getElementById('start-quiz-btn');
            if (startBtn) {
                startBtn.addEventListener('click', () => {
                    this.currentView = 'study';
                    this.loadNextQuestion();
                });
            }
            
            const nextBtn = document.getElementById('next-btn');
            if (nextBtn) {
                nextBtn.addEventListener('click', () => this.loadNextQuestion());
            }
        },
        
        async generateQuestionForTopic(topicId) {
            this.currentView = 'study';
            await this.$nextTick();
            
            const quizSection = document.getElementById('quiz-section');
            const noQuizMessage = document.getElementById('no-quiz-message');
            
            if (quizSection) quizSection.style.display = 'block';
            if (noQuizMessage) noQuizMessage.style.display = 'none';
            
            document.getElementById('question-text').textContent = 'Loading question...';
            document.getElementById('options-container').innerHTML = '';
            document.getElementById('feedback').style.display = 'none';
            document.getElementById('next-btn').style.display = 'none';
            document.getElementById('guide-me-container').style.display = 'block';
            
            try {
                const response = await fetch('/generate-question', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ topic_id: topicId })
                });
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('question-text').textContent = 'Error: ' + data.error;
                    return;
                }
                
                this.currentQuestion = data;
                this.displayQuestion(data);
            } catch (err) {
                document.getElementById('question-text').textContent = 'Error: ' + err.message;
            }
        },
        
        async loadNextQuestion() {
            const quizSection = document.getElementById('quiz-section');
            const noQuizMessage = document.getElementById('no-quiz-message');
            
            if (quizSection) quizSection.style.display = 'block';
            if (noQuizMessage) noQuizMessage.style.display = 'none';
            
            document.getElementById('question-text').textContent = 'Loading question...';
            document.getElementById('options-container').innerHTML = '';
            document.getElementById('feedback').style.display = 'none';
            document.getElementById('next-btn').style.display = 'none';
            document.getElementById('guide-me-container').style.display = 'block';
            
            try {
                const response = await fetch('/generate-question', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('question-text').textContent = 'Error: ' + data.error;
                    return;
                }
                
                this.currentQuestion = data;
                this.displayQuestion(data);
            } catch (err) {
                document.getElementById('question-text').textContent = 'Error: ' + err.message;
            }
        },
        
        displayQuestion(question) {
            document.getElementById('topic-name').textContent = question.topic_name;
            const badge = document.getElementById('difficulty-badge');
            badge.textContent = question.difficulty.toUpperCase();
            badge.className = `px-4 py-1 rounded-full text-sm font-medium ${question.difficulty}`;
            
            document.getElementById('question-text').innerHTML = question.question;
            
            const optionsContainer = document.getElementById('options-container');
            optionsContainer.innerHTML = '';
            
            question.options.forEach((option, index) => {
                const btn = document.createElement('button');
                btn.className = 'option-btn';
                btn.innerHTML = option;
                btn.addEventListener('click', () => this.selectAnswer(index));
                optionsContainer.appendChild(btn);
            });
            
            if (window.MathJax) {
                MathJax.typesetPromise();
            }
        },
        
        async selectAnswer(selectedIndex) {
            const isCorrect = selectedIndex === this.currentQuestion.correct_answer;
            
            const options = document.querySelectorAll('.option-btn');
            options.forEach((btn, index) => {
                btn.disabled = true;
                if (index === this.currentQuestion.correct_answer) {
                    btn.classList.add('correct');
                } else if (index === selectedIndex && !isCorrect) {
                    btn.classList.add('wrong');
                }
            });
            
            const feedbackDiv = document.getElementById('feedback');
            const feedbackText = document.getElementById('feedback-text');
            const explanationText = document.getElementById('explanation');
            
            feedbackText.textContent = isCorrect ? '✓ Correct!' : '✗ Incorrect';
            feedbackText.className = isCorrect ? 'correct-text' : 'wrong-text';
            explanationText.innerHTML = this.currentQuestion.explanation;
            feedbackDiv.style.display = 'block';
            document.getElementById('next-btn').style.display = 'block';
            document.getElementById('guide-me-container').style.display = 'none';
            
            if (window.MathJax) {
                MathJax.typesetPromise();
            }
            
            try {
                const response = await fetch('/submit-answer', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        topic_id: this.currentQuestion.topic_id,
                        is_correct: isCorrect
                    })
                });
                
                const data = await response.json();
                
                if (data.success && data.user_state) {
                    // Update stats directly from response
                    this.updateStatsFromData({ user_state: data.user_state });
                    
                    // Update XP if provided
                    if (data.xp_progress) {
                        this.xpProgress = data.xp_progress;
                    }
                    
                    // Show achievements if any
                    if (data.new_achievements && data.new_achievements.length > 0) {
                        const achievementNames = data.new_achievements.map(a => a.achievement_name || a.name || 'Achievement').join(', ');
                        alert(`🎉 Achievement Unlocked: ${achievementNames}!`);
                    }
                } else {
                    // Fallback to loading stats
                    this.loadStats();
                }
            } catch (err) {
                console.error('Error submitting answer:', err);
                // Still try to load stats on error
                this.loadStats();
            }
        },
        async openGuideMeModal() {
            if (!this.currentQuestion) return;
            
            this.showGuideMeModal = true;
            const content = document.getElementById('guide-me-content');
            
            if (content) {
                content.innerHTML = '<div class="spinner mx-auto"></div>';
            }
            
            try {
                const response = await fetch('/guide-me', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        question: this.currentQuestion.question,
                        topic: this.currentQuestion.topic_name,
                        difficulty: this.currentQuestion.difficulty
                    })
                });
                const data = await response.json();
                
                if (data.error) {
                    if (content) content.innerHTML = `<p class="text-red-400">Error: ${data.error}</p>`;
                    return;
                }
                
                this.guideMeSteps = data.sub_questions || [];
                this.currentGuideMeStep = 0;
                this.renderGuideMeStep();
            } catch (err) {
                if (content) content.innerHTML = `<p class="text-red-400">Error: ${err.message}</p>`;
            }
        },
        
        renderGuideMeStep() {
            const content = document.getElementById('guide-me-content');
            if (!content || !this.guideMeSteps.length) return;
            
            const step = this.guideMeSteps[this.currentGuideMeStep];
            const stepNum = this.currentGuideMeStep + 1;
            const totalSteps = this.guideMeSteps.length;
            
            content.innerHTML = `
                <div class="mb-6">
                    <div class="flex items-center justify-between mb-4">
                        <span class="text-sm font-medium text-slate-400">Step ${stepNum} of ${totalSteps}</span>
                        <div class="flex space-x-1">
                            ${Array.from({ length: totalSteps }, (_, i) => `
                                <div class="w-8 h-1 rounded ${i < stepNum ? 'bg-blue-500' : 'bg-slate-600'}"></div>
                            `).join('')}
                        </div>
                    </div>
                    
                    <p class="text-lg mb-4">${step.question}</p>
                    
                    ${step.hint ? `<div class="bg-slate-700 rounded-lg p-3 mb-4 text-sm">
                        <span class="font-semibold">💡 Hint:</span> ${step.hint}
                    </div>` : ''}
                    
                    <div class="space-y-2">
                        ${step.options?.map((opt, idx) => `
                            <button class="option-btn" onclick="window.checkGuideMeAnswer(${idx})">
                                ${opt}
                            </button>
                        `).join('') || ''}
                    </div>
                    
                    <div id="guide-me-step-feedback" class="mt-4"></div>
                </div>
            `;
            
            if (window.MathJax) {
                MathJax.typesetPromise();
            }
        },
        
        checkGuideMeAnswer(selectedIdx) {
            const step = this.guideMeSteps[this.currentGuideMeStep];
            const isCorrect = selectedIdx === step.correct_answer;
            const feedback = document.getElementById('guide-me-step-feedback');
            
            if (isCorrect) {
                feedback.innerHTML = `
                    <div class="bg-green-900/50 border border-green-500 rounded-lg p-4">
                        <p class="text-green-400 font-semibold mb-2">✓ Correct!</p>
                        ${step.explanation ? `<p class="text-sm text-slate-300">${step.explanation}</p>` : ''}
                        <button class="mt-3 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm" 
                                onclick="window.nextGuideMeStep()">
                            ${this.currentGuideMeStep < this.guideMeSteps.length - 1 ? 'Next Step →' : 'Finish'}
                        </button>
                    </div>
                `;
            } else {
                feedback.innerHTML = `
                    <div class="bg-red-900/50 border border-red-500 rounded-lg p-4">
                        <p class="text-red-400 font-semibold">✗ Not quite. Try again!</p>
                    </div>
                `;
            }
        },
        
        nextGuideMeStep() {
            this.currentGuideMeStep++;
            if (this.currentGuideMeStep >= this.guideMeSteps.length) {
                this.closeGuideMeModal();
                // Award bonus XP
                alert('🎉 Great job! You earned +20% bonus XP for using Guide Me!');
            } else {
                this.renderGuideMeStep();
            }
        },
        
        closeGuideMeModal() {
            this.showGuideMeModal = false;
            this.guideMeSteps = [];
            this.currentGuideMeStep = 0;
        },
        
        setupExamPrepForm() {
            const form = document.getElementById('exam-prep-form');
            if (form) {
                form.addEventListener('submit', (e) => {
                    e.preventDefault();
                    this.createExamPlan();
                });
            }
        },
        
        populateExamTopics(topics) {
            const container = document.getElementById('exam-topics-selector');
            if (!container) return;
            
            container.innerHTML = topics.map((topic, idx) => `
                <label class="flex items-center space-x-2 p-2 hover:bg-slate-600 rounded cursor-pointer">
                    <input type="checkbox" value="${topic.topic_id}" 
                           class="exam-topic-checkbox rounded border-slate-500">
                    <span class="text-sm">${topic.name}</span>
                </label>
            `).join('');
        },
        
        async createExamPlan() {
            const examName = document.getElementById('exam-name').value;
            const examDate = document.getElementById('exam-date').value;
            const selectedTopics = Array.from(document.querySelectorAll('.exam-topic-checkbox:checked'))
                .map(cb => cb.value);
            
            if (!examName || !examDate || selectedTopics.length === 0) {
                alert('Please fill in all fields and select at least one topic');
                return;
            }
            
            try {
                const response = await fetch('/exam-prep/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        exam_name: examName,
                        exam_date: examDate,
                        topics: selectedTopics
                    })
                });
                const data = await response.json();
                
                if (data.error) {
                    alert('Error: ' + data.error);
                    return;
                }
                
                this.displayExamReadiness(data);
            } catch (err) {
                alert('Error: ' + err.message);
            }
        },
        
        displayExamReadiness(data) {
            document.getElementById('exam-readiness-dashboard').style.display = 'block';
            document.getElementById('overall-readiness').textContent = Math.round(data.overall_readiness || 0) + '%';
            document.getElementById('days-until-exam').textContent = data.days_until_exam || 0;
            document.getElementById('predicted-score').textContent = Math.round(data.predicted_score || 0) + '%';
            
            const topicsList = document.getElementById('topic-readiness-list');
            topicsList.innerHTML = (data.topic_readiness || []).map(topic => `
                <div>
                    <div class="flex justify-between mb-1">
                        <span class="text-sm font-medium">${topic.topic_id}</span>
                        <span class="text-sm text-slate-400">${Math.round(topic.current_mastery * 100)}%</span>
                    </div>
                    <div class="progress-bar-track">
                        <div class="progress-bar-fill" style="width: ${topic.current_mastery * 100}%"></div>
                    </div>
                </div>
            `).join('');
            
            const goalsList = document.getElementById('daily-goals-list');
            goalsList.innerHTML = (data.daily_goals || []).map(goal => `
                <div class="flex justify-between items-center p-3 bg-slate-700 rounded-lg">
                    <span class="text-sm">${goal.topic_id}</span>
                    <span class="text-sm font-medium text-blue-400">${goal.daily_questions} questions/day</span>
                </div>
            `).join('');
        },
        
        setupSettingsButtons() {
            const saveBtn = document.getElementById('save-progress-btn');
            if (saveBtn) {
                saveBtn.addEventListener('click', () => this.saveProgress());
            }
            
            const loadBtn = document.getElementById('load-progress-btn');
            if (loadBtn) {
                loadBtn.addEventListener('click', () => this.loadProgress());
            }
            
            const exportBtn = document.getElementById('export-report-btn');
            if (exportBtn) {
                exportBtn.addEventListener('click', () => this.exportReport());
            }
        },
        
        async saveProgress() {
            const status = document.getElementById('settings-status');
            try {
                const response = await fetch('/save-progress', { method: 'POST' });
                const data = await response.json();
                status.textContent = data.message || 'Progress saved!';
                status.className = 'mt-3 text-sm text-green-400';
            } catch (err) {
                status.textContent = 'Error: ' + err.message;
                status.className = 'mt-3 text-sm text-red-400';
            }
        },
        
        async loadProgress() {
            const status = document.getElementById('settings-status');
            try {
                const response = await fetch('/load-progress', { method: 'POST' });
                const data = await response.json();
                status.textContent = data.message || 'Progress loaded!';
                status.className = 'mt-3 text-sm text-green-400';
                this.loadStats();
            } catch (err) {
                status.textContent = 'Error: ' + err.message;
                status.className = 'mt-3 text-sm text-red-400';
            }
        },
        
        async exportReport() {
            const status = document.getElementById('settings-status');
            try {
                const response = await fetch('/export-report', { method: 'POST' });
                const data = await response.json();
                status.textContent = data.message || 'Report exported!';
                status.className = 'mt-3 text-sm text-green-400';
            } catch (err) {
                status.textContent = 'Error: ' + err.message;
                status.className = 'mt-3 text-sm text-red-400';
            }
        },
        
        async clearUserData() {
            if (!confirm('Are you sure you want to delete all your progress? This cannot be undone.')) {
                return;
            }
            
            // In production, this would call a backend endpoint
            alert('Feature not yet implemented in this demo');
        },
        
        async loadLeaderboard() {
            try {
                const response = await fetch(
                    `/leaderboard/${this.leaderboardType}?period=${this.leaderboardPeriod}`
                );
                const data = await response.json();
                
                if (data.leaderboard) {
                    this.leaderboardData = data.leaderboard;
                    this.renderLeaderboard(data.leaderboard);
                }
                
                // Get my rank
                const rankResponse = await fetch(
                    `/leaderboard/my-rank?type=${this.leaderboardType}&period=${this.leaderboardPeriod}`
                );
                const rankData = await rankResponse.json();
                
                if (rankData.user_rank) {
                    this.myRank = rankData.user_rank.rank;
                    this.totalUsers = rankData.total_users;
                }
            } catch (err) {
                console.error('Error loading leaderboard:', err);
            }
        },
        
        renderLeaderboard(leaderboard) {
            const container = document.getElementById('leaderboard-list');
            if (!container) return;
            
            if (leaderboard.length === 0) {
                container.innerHTML = '<div class="p-6 text-center text-slate-400">No data available</div>';
                return;
            }
            
            container.innerHTML = leaderboard.map(user => {
                const isCurrentUser = user.user_id === this.currentUser.user_id;
                const medal = user.rank === 1 ? '🥇' : user.rank === 2 ? '🥈' : user.rank === 3 ? '🥉' : '';
                
                return `
                    <div class="p-4 flex items-center justify-between ${isCurrentUser ? 'bg-blue-900/30' : 'hover:bg-slate-700'}">
                        <div class="flex items-center space-x-4">
                            <span class="text-2xl font-bold text-slate-400 w-12">${medal || '#' + user.rank}</span>
                            <div>
                                <div class="font-medium ${isCurrentUser ? 'text-blue-400' : ''}">
                                    ${user.username} ${isCurrentUser ? '(You)' : ''}
                                </div>
                                <div class="text-xs text-slate-400">${user.major || 'No major'}</div>
                            </div>
                        </div>
                        <div class="flex items-center space-x-6">
                            <div class="text-right">
                                <div class="font-bold text-lg">${user.total_xp}</div>
                                <div class="text-xs text-slate-400">XP</div>
                            </div>
                            <div class="text-right">
                                <div class="font-bold">${user.study_streak || 0}🔥</div>
                                <div class="text-xs text-slate-400">Streak</div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        },
        
        async loadDocuments() {
            try {
                const response = await fetch('/documents');
                const data = await response.json();
                if (response.ok) {
                    this.documents = data.documents || [];
                }
            } catch (err) {
                console.error('Error loading documents:', err);
            }
        },
        
        async loadDocument(documentId) {
            try {
                const response = await fetch(`/documents/${documentId}/load`, {
                    method: 'POST'
                });
                const data = await response.json();
                
                if (response.ok) {
                    alert('Document loaded successfully! Topics are now available for study.');
                    this.allTopics = data.topics || [];
                    this.currentView = 'home';
                    // Refresh topics display if on home view
                    if (this.allTopics.length > 0) {
                        this.displayTopics(this.allTopics);
                    }
                } else {
                    alert('Error: ' + (data.error || 'Failed to load document'));
                }
            } catch (err) {
                console.error('Error loading document:', err);
                alert('Error loading document');
            }
        },
        
        async deleteDocument(documentId) {
            if (!confirm('Are you sure you want to delete this document?')) {
                return;
            }
            
            try {
                const response = await fetch(`/documents/${documentId}/delete`, {
                    method: 'DELETE'
                });
                const data = await response.json();
                
                if (response.ok) {
                    // Remove from list
                    this.documents = this.documents.filter(d => d.document_id !== documentId);
                    alert('Document deleted successfully');
                } else {
                    alert('Error: ' + (data.error || 'Failed to delete document'));
                }
            } catch (err) {
                console.error('Error deleting document:', err);
                alert('Error deleting document');
            }
        },
        
        formatFileSize(bytes) {
            if (!bytes) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
        },
        
        formatDate(dateString) {
            if (!dateString) return '';
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'short', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        },
        
        // Exam Questions Functions
        async loadExams() {
            try {
                const response = await fetch('/exam/list');
                const data = await response.json();
                if (response.ok) {
                    this.exams = data.exams || [];
                } else {
                    console.error('Error loading exams:', data.error);
                }
            } catch (err) {
                console.error('Error loading exams:', err);
            }
        },
        
        async uploadExam() {
            const form = document.getElementById('exam-upload-form');
            const fileInput = document.getElementById('exam-file-input');
            const statusDiv = document.getElementById('exam-upload-status');
            
            if (!fileInput.files.length) {
                statusDiv.textContent = 'Please select a file';
                return;
            }
            
            if (!this.examUploadForm.examName) {
                statusDiv.textContent = 'Please enter an exam name';
                return;
            }
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('exam_name', this.examUploadForm.examName);
            
            statusDiv.textContent = 'Uploading and extracting questions...';
            
            try {
                statusDiv.textContent = 'Uploading and extracting questions...';
                statusDiv.className = 'text-sm mt-2 text-center text-slate-400';
                
                const response = await fetch('/exam/upload', {
                    method: 'POST',
                    body: formData
                });
                
                let data;
                try {
                    data = await response.json();
                } catch (jsonErr) {
                    console.error('Failed to parse response:', jsonErr);
                    statusDiv.textContent = 'Error: Invalid response from server';
                    statusDiv.className = 'text-sm mt-2 text-center text-red-400';
                    return;
                }
                
                if (response.ok && data.success) {
                    if (data.status === 'processing') {
                        // Incremental processing started
                        statusDiv.textContent = 'Upload started! Processing pages in background. Questions will appear as they are extracted...';
                        statusDiv.className = 'text-sm mt-2 text-center text-blue-400';
                        this.examUploadForm.examName = '';
                        fileInput.value = '';
                        this.loadExams();
                        
                        // Poll for progress
                        this.pollExamProgress(data.exam_id);
                    } else {
                        // Completed immediately (single image)
                        statusDiv.textContent = `Success! Extracted ${data.total_questions || 0} questions from ${data.total_pages || 0} pages.`;
                        statusDiv.className = 'text-sm mt-2 text-center text-green-400';
                        this.examUploadForm.examName = '';
                        fileInput.value = '';
                        this.loadExams();
                    }
                } else {
                    const errorMsg = data.error || 'Upload failed';
                    statusDiv.textContent = 'Error: ' + errorMsg;
                    statusDiv.className = 'text-sm mt-2 text-center text-red-400';
                    console.error('Upload error:', data);
                }
            } catch (err) {
                statusDiv.textContent = 'Error: ' + (err.message || 'Network error. Please check your connection.');
                statusDiv.className = 'text-sm mt-2 text-center text-red-400';
                console.error('Upload error:', err);
            }
        },
        
        async analyzeExam(examId) {
            if (!confirm('This will analyze all questions using AI. This may take a while. Continue?')) {
                return;
            }
            
            try {
                const response = await fetch(`/exam/${examId}/analyze`, {
                    method: 'POST'
                });
                const data = await response.json();
                
                if (response.ok && data.success) {
                    alert(data.message || `Analysis started for ${data.total} questions. This may take a while.`);
                    this.loadExams();
                    // Start polling for progress
                    this.pollExamProgress(examId);
                    if (this.selectedExamQuestions.length > 0) {
                        // Refresh questions if viewing
                        this.viewExamQuestions(examId);
                    }
                } else {
                    alert('Error: ' + (data.error || 'Analysis failed'));
                }
            } catch (err) {
                console.error('Analysis error:', err);
                alert('Error analyzing exam');
            }
        },
        
        pollExamProgress(examId) {
            // Poll every 3 seconds for progress updates
            const maxPolls = 60; // Poll for up to 3 minutes
            let pollCount = 0;
            
            const pollInterval = setInterval(async () => {
                pollCount++;
                if (pollCount > maxPolls) {
                    clearInterval(pollInterval);
                    const statusDiv = document.getElementById('exam-upload-status');
                    if (statusDiv) {
                        statusDiv.textContent = 'Processing is taking longer than expected. Please refresh the page.';
                        statusDiv.className = 'text-sm mt-2 text-center text-yellow-400';
                    }
                    return;
                }
                
                try {
                    const response = await fetch('/exam/list');
                    const data = await response.json();
                    if (response.ok && data.exams) {
                        const exam = data.exams.find(e => e.exam_id === examId);
                        if (exam) {
                            // Update status display
                            const statusDiv = document.getElementById('exam-upload-status');
                            if (statusDiv) {
                                if (exam.is_processing) {
                                    if (exam.is_analyzing) {
                                        statusDiv.textContent = `Analyzing questions... ${exam.analyzed_questions} of ${exam.total_questions} analyzed.`;
                                    } else if (exam.current_page) {
                                        statusDiv.textContent = `Extracting page ${exam.current_page} of ${exam.total_pages}... ${exam.total_questions} questions extracted so far.`;
                                    } else {
                                    statusDiv.textContent = `Processing... ${exam.total_questions} questions extracted so far from ${exam.total_pages} pages.`;
                                    }
                                    statusDiv.className = 'text-sm mt-2 text-center text-blue-400';
                                } else {
                                    // Processing complete
                                    statusDiv.textContent = `Complete! Extracted ${exam.total_questions} questions from ${exam.total_pages} pages. ${exam.analyzed_questions} analyzed.`;
                                    statusDiv.className = 'text-sm mt-2 text-center text-green-400';
                                    clearInterval(pollInterval);
                                }
                            }
                            
                            // Refresh exam list
                            this.loadExams();
                            
                            // Stop polling if not processing
                            if (!exam.is_processing) {
                                clearInterval(pollInterval);
                            }
                        }
                    }
                } catch (err) {
                    console.error('Error polling exam progress:', err);
                }
            }, 3000); // Poll every 3 seconds
        },
        
        async retryExamProcessing(examId) {
            if (!confirm('This will re-process the exam file. Continue?')) {
                return;
            }
            try {
                const response = await fetch(`/exam/${examId}/retry`, {
                    method: 'POST'
                });
                const data = await response.json();
                if (response.ok) {
                    alert('Processing restarted. Questions will appear as they are extracted.');
                    this.loadExams();
                    this.pollExamProgress(examId);
                } else {
                    alert('Error: ' + (data.error || 'Failed to retry processing'));
                }
            } catch (err) {
                console.error('Retry error:', err);
                alert('Error retrying exam processing');
            }
        },
        
        async viewExamQuestions(examId) {
            try {
                console.log('[VIEW_QUESTIONS] Loading questions for exam:', examId);
                
                // Set to empty array first to show loading state
                this.selectedExamQuestions = [];
                
                const response = await fetch(`/exam/${examId}/questions`);
                const data = await response.json();
                
                console.log('[VIEW_QUESTIONS] Response:', data);
                
                if (response.ok) {
                    // Process questions with error handling
                    this.selectedExamQuestions = (data.questions || []).map(q => {
                        try {
                            // Ensure all required fields exist
                            const processed = {
                                ...q,
                                activeTab: 'question',  // Initialize tab state
                                text: q.text || q.question_text || '',
                                options: q.options || [],
                                analyzed: q.analyzed || false
                            };
                            return processed;
                        } catch (err) {
                            console.error('[VIEW_QUESTIONS] Error processing question:', err, q);
                            return {
                                question_id: q.question_id || 0,
                                text: 'Error loading question',
                                activeTab: 'question',
                                options: [],
                                analyzed: false
                            };
                        }
                    });
                    
                    console.log('[VIEW_QUESTIONS] Loaded', this.selectedExamQuestions.length, 'questions');
                    
                    // Initialize lazy loading for MathJax after DOM updates
                    this.$nextTick(() => {
                        setTimeout(() => {
                            this.initMathJaxLazyLoading();
                            // Re-initialize after a longer delay to catch all dynamically added content
                            setTimeout(() => {
                                this.initMathJaxLazyLoading();
                            }, 500);
                        }, 100);
                    });
                    
                    // Scroll to questions section (whether empty or not)
                    setTimeout(() => {
                        // Try to find the questions section or empty state
                        const questionsSection = document.querySelector('[x-show*="selectedExamQuestions"]');
                        if (questionsSection) {
                            questionsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        } else {
                            // Fallback: scroll to exam questions view
                            const examView = document.querySelector('[x-show="currentView === \'exam-questions\'"]');
                            if (examView) {
                                examView.scrollIntoView({ behavior: 'smooth', block: 'start' });
                            }
                        }
                    }, 100);
                } else {
                    console.error('[VIEW_QUESTIONS] Error response:', data);
                    this.selectedExamQuestions = null; // Reset to null on error
                    alert('Error: ' + (data.error || 'Failed to load questions'));
                }
            } catch (err) {
                console.error('[VIEW_QUESTIONS] Exception:', err);
                this.selectedExamQuestions = null; // Reset to null on error
                alert('Error loading questions: ' + err.message);
            }
        },
        
        async deleteExam(examId) {
            if (!confirm('Are you sure you want to delete this exam? This will delete all questions and associated data.')) {
                return;
            }
            
            try {
                const response = await fetch(`/exam/${examId}/delete`, {
                    method: 'DELETE'
                });
                const data = await response.json();
                
                if (response.ok) {
                    // Remove from list
                    this.exams = this.exams.filter(e => e.exam_id !== examId);
                    // Clear selected questions if viewing this exam
                    if (this.selectedExamQuestions && this.selectedExamQuestions.length > 0) {
                        // Check if we're viewing this exam's questions
                        const firstQuestion = this.selectedExamQuestions[0];
                        if (firstQuestion && this.exams.find(e => e.exam_id === examId) === undefined) {
                            this.selectedExamQuestions = null;
                        }
                    }
                    alert('Exam deleted successfully');
                } else {
                    alert('Error: ' + (data.error || 'Failed to delete exam'));
                }
            } catch (err) {
                console.error('Error deleting exam:', err);
                alert('Error deleting exam');
            }
        },
        
        formatQuestionText(text) {
            if (!text) return '';
            // Escape HTML and preserve line breaks
            let formatted = text
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/\n/g, '<br>');
            
            // MathJax will handle LaTeX rendering automatically
            return formatted;
        },
        
        renderMath(text) {
            if (!text) return '';
            
            try {
                // Escape HTML but preserve LaTeX delimiters
                let processed = String(text)
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;');
                
                // Convert newlines to <br>
                processed = processed.replace(/\n/g, '<br>');
                
                // Add class to mark for MathJax processing (lazy loading)
                // MathJax will be triggered by Intersection Observer for visible elements
                return processed;
            } catch (err) {
                console.error('Error in renderMath:', err);
                return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            }
        },
        
        // Debounced MathJax rendering function
        mathJaxRenderQueue: [],
        mathJaxRenderTimer: null,
        
        queueMathJaxRender(element) {
            // Add element to queue if not already queued
            if (!this.mathJaxRenderQueue.includes(element)) {
                this.mathJaxRenderQueue.push(element);
            }
            
            // Debounce: wait 100ms before rendering to batch multiple calls
            clearTimeout(this.mathJaxRenderTimer);
            this.mathJaxRenderTimer = setTimeout(() => {
                this.processMathJaxQueue();
            }, 100);
        },
        
        async processMathJaxQueue() {
            if (this.mathJaxRenderQueue.length === 0) return;
            
            // Wait for MathJax to be ready
            if (window.MathJax && window.MathJax.startup && window.MathJax.startup.promise) {
                try {
                    await window.MathJax.startup.promise;
                } catch (e) {
                    console.log('MathJax startup error:', e);
                }
            }
            
            if (!window.MathJax || !window.MathJax.typesetPromise) {
                console.log('MathJax not ready yet');
                return;
            }
            
            // Filter to only visible elements
            const visibleElements = this.mathJaxRenderQueue.filter(el => {
                if (!el || !document.contains(el)) return false;
                const rect = el.getBoundingClientRect();
                return rect.top < window.innerHeight + 500 && rect.bottom > -500; // 500px buffer
            });
            
            if (visibleElements.length === 0) {
                this.mathJaxRenderQueue = [];
                return;
            }
            
            try {
                // Render only visible elements
                await window.MathJax.typesetPromise(visibleElements);
                
                // Remove rendered elements from queue
                this.mathJaxRenderQueue = this.mathJaxRenderQueue.filter(
                    el => !visibleElements.includes(el)
                );
            } catch (err) {
                console.log('MathJax rendering error:', err);
                // Clear queue on error to prevent infinite retries
                this.mathJaxRenderQueue = [];
            }
        },
        
        // Initialize lazy loading for MathJax
        initMathJaxLazyLoading() {
            // Wait for MathJax to load
            if (!window.MathJax) {
                setTimeout(() => this.initMathJaxLazyLoading(), 100);
                return;
            }
            
            // Clean up existing observer if any
            if (this.mathJaxObserver) {
                this.mathJaxObserver.disconnect();
            }
            
            // Create Intersection Observer for lazy loading
            const observerOptions = {
                root: null,
                rootMargin: '200px', // Start rendering 200px before element is visible
                threshold: 0.01
            };
            
            const self = this;
            const mathObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const element = entry.target;
                        // Mark as processed
                        element.setAttribute('data-mathjax-processed', 'true');
                        // Queue for rendering
                        self.queueMathJaxRender(element);
                        // Stop observing once processed
                        mathObserver.unobserve(element);
                    }
                });
            }, observerOptions);
            
            // Observe all elements with math content
            setTimeout(() => {
                const mathElements = document.querySelectorAll('.mathjax-process');
                mathElements.forEach(el => {
                    if (!el.getAttribute('data-mathjax-processed')) {
                        mathObserver.observe(el);
                    }
                });
                
                // Also observe any new elements that might be added dynamically
                // Re-run observer setup when questions are loaded
                if (this.selectedExamQuestions && this.selectedExamQuestions.length > 0) {
                    // Re-observe after a short delay to catch dynamically added content
                    setTimeout(() => {
                        const newMathElements = document.querySelectorAll('.mathjax-process:not([data-mathjax-processed])');
                        newMathElements.forEach(el => {
                            mathObserver.observe(el);
                        });
                    }, 500);
                }
            }, 200);
            
            // Store observer for cleanup
            this.mathJaxObserver = mathObserver;
        },
        
        async loadAchievements() {
            try {
                const response = await fetch('/achievements');
                const data = await response.json();
                
                if (data.achievements) {
                    this.allAchievements = data.achievements;
                }
            } catch (err) {
                console.error('Error loading achievements:', err);
            }
        },
        
        async loadActivityFeed() {
            try {
                const response = await fetch('/activity/recent?limit=10');
                const data = await response.json();
                
                if (data.activities) {
                    this.renderActivityFeed(data.activities);
                }
            } catch (err) {
                console.error('Error loading activity feed:', err);
            }
        },
        
        renderActivityFeed(activities) {
            const container = document.getElementById('activity-feed');
            if (!container) return;
            
            if (activities.length === 0) {
                container.innerHTML = '<div class="text-xs text-slate-400">No recent activity</div>';
                return;
            }
            
            container.innerHTML = activities.map(activity => {
                const timeAgo = this.formatTimeAgo(activity.timestamp);
                
                return `
                    <div class="flex items-start space-x-2 text-xs">
                        <span class="text-lg">${activity.icon}</span>
                        <div class="flex-1">
                            <p class="text-slate-300">${activity.message}</p>
                            <p class="text-slate-500 mt-1">${timeAgo}</p>
                        </div>
                    </div>
                `;
            }).join('');
        },
        
        formatTimeAgo(timestamp) {
            const now = new Date();
            const past = new Date(timestamp);
            const seconds = Math.floor((now - past) / 1000);
            
            if (seconds < 60) return 'Just now';
            if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
            if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
            return `${Math.floor(seconds / 86400)}d ago`;
        }
    };
}

// Global functions for Guide Me
window.checkGuideMeAnswer = function(idx) {
    const appEl = document.querySelector('[x-data]');
    if (appEl && appEl.__x) {
        appEl.__x.$data.checkGuideMeAnswer(idx);
    }
};

window.nextGuideMeStep = function() {
    const appEl = document.querySelector('[x-data]');
    if (appEl && appEl.__x) {
        appEl.__x.$data.nextGuideMeStep();
    }
};

