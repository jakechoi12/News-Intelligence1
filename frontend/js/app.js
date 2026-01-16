/**
 * News Intelligence - Frontend Application
 * Updated: v2.1 - New layout with distribution bars, Google Finance style indicators
 */

// State
const state = {
    newsData: null,
    mapData: null,
    wordcloudData: null,
    economicData: null,
    lastUpdate: null,
    headlinesData: null,  // Headlines with insights
    
    // Filters
    currentFilter: 'all',
    currentCategory: null,
    currentSentiment: null,  // NEW: positive, neutral, negative
    currentPage: 1,
    itemsPerPage: 10,
    
    // Charts
    map: null,
    economicChart: null,
    currentEconomicType: 'stock',
    currentPeriod: '1M',
    selectedIndicator: null,
};

// Category Colors
const CATEGORY_COLORS = {
    Crisis: '#ef4444',
    Ocean: '#3b82f6',
    Air: '#10b981',
    Inland: '#f59e0b',
    Economy: '#8b5cf6',
    ETC: '#6b7280',
};

// Country Colors (for top countries)
const COUNTRY_COLORS = {
    US: '#ef4444',
    CN: '#f59e0b',
    KR: '#3b82f6',
    JP: '#10b981',
    DE: '#8b5cf6',
    SG: '#06b6d4',
    TW: '#ec4899',
    VN: '#14b8a6',
    IN: '#f97316',
    NL: '#a855f7',
    GB: '#0ea5e9',
    FR: '#6366f1',
    RU: '#dc2626',
    UA: '#eab308',
    Others: '#6b7280',
};

// Sentiment Colors
const SENTIMENT_COLORS = {
    positive: '#10b981',  // Green
    neutral: '#6b7280',   // Gray
    negative: '#ef4444',  // Red
};

// Base URL for data files
const DATA_BASE_URL = './data';

/**
 * Initialize application
 */
async function init() {
    console.log('📰 News Intelligence initializing...');
    
    try {
        // Load all data in parallel
        await Promise.all([
            loadNewsData(),
            loadHeadlinesData(),
            loadMapData(),
            loadWordcloudData(),
            loadEconomicData(),
            loadLastUpdate(),
        ]);
        
        // Render UI
        renderSummary();
        renderTicker();
        renderWordcloud();
        renderHeadlines();
        initMap();
        renderEconomicSection();
        renderDistributionBars();
        renderNewsList();
        
        // Setup event listeners
        setupEventListeners();
        
        console.log('✅ News Intelligence ready!');
    } catch (error) {
        console.error('❌ Failed to initialize:', error);
        showError('Failed to load data. Please try again later.');
    }
}

/**
 * Data Loading Functions
 */
async function loadNewsData() {
    try {
        const response = await fetch(`${DATA_BASE_URL}/news_data.json`);
        if (!response.ok) throw new Error('Failed to load news data');
        state.newsData = await response.json();
        console.log(`📰 Loaded ${state.newsData.total} articles`);
    } catch (e) {
        console.warn('Using mock news data');
        state.newsData = createMockNewsData();
    }
}

async function loadHeadlinesData() {
    try {
        const response = await fetch(`${DATA_BASE_URL}/headlines_data.json`);
        if (!response.ok) throw new Error('Failed to load headlines data');
        state.headlinesData = await response.json();
        console.log(`📰 Loaded ${state.headlinesData.headlines?.length || 0} headlines`);
    } catch (e) {
        state.headlinesData = { headlines: [] };
    }
}

async function loadMapData() {
    try {
        const response = await fetch(`${DATA_BASE_URL}/map_data.json`);
        if (!response.ok) throw new Error('Failed to load map data');
        state.mapData = await response.json();
        console.log(`🗺️ Loaded map data for ${state.mapData.countries?.length || 0} countries`);
    } catch (e) {
        state.mapData = { countries: [] };
    }
}

async function loadWordcloudData() {
    try {
        const response = await fetch(`${DATA_BASE_URL}/wordcloud_data.json`);
        if (!response.ok) throw new Error('Failed to load wordcloud data');
        state.wordcloudData = await response.json();
        console.log(`💬 Loaded ${state.wordcloudData.keywords?.length || 0} keywords`);
    } catch (e) {
        state.wordcloudData = { keywords: [] };
    }
}

async function loadEconomicData() {
    try {
        const response = await fetch(`${DATA_BASE_URL}/economic_data.json`);
        if (response.ok) {
            const loadedData = await response.json();
            
            // Check if data has enough points (at least 90 for 3M)
            const sampleData = loadedData?.stock_index?.items?.KOSPI?.data || [];
            if (sampleData.length < 90) {
                console.log(`📊 Loaded data only has ${sampleData.length} points, using mock data for better visualization`);
                state.economicData = createMockEconomicData();
            } else {
                state.economicData = loadedData;
                console.log(`📊 Loaded economic data (${sampleData.length} points)`);
            }
        } else {
            state.economicData = createMockEconomicData();
            console.log(`📊 Using mock economic data`);
        }
    } catch {
        state.economicData = createMockEconomicData();
        console.log(`📊 Using mock economic data`);
    }
}

async function loadLastUpdate() {
    try {
        const response = await fetch(`${DATA_BASE_URL}/last_update.json`);
        if (!response.ok) throw new Error('Failed to load update info');
        state.lastUpdate = await response.json();
        
        const updateEl = document.getElementById('last-update');
        if (updateEl && state.lastUpdate.executed_at_kst) {
            updateEl.textContent = formatDateTime(state.lastUpdate.executed_at_kst);
        }
    } catch (e) {
        document.getElementById('last-update').textContent = 'No data';
    }
}

/**
 * Mock Data Generators
 */
function createMockNewsData() {
    return {
        articles: [],
        total: 0,
        kr_count: 0,
        global_count: 0,
        crisis_count: 0,
        categories: { Crisis: 0, Ocean: 0, Air: 0, Inland: 0, Economy: 0, ETC: 0 },
    };
}

function createMockEconomicData() {
    const generateData = (base, variance, days = 365) => {
        const data = [];
        let value = base;
        for (let i = days; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            value = value + (Math.random() - 0.5) * variance;
            data.push({
                time: date.toISOString().split('T')[0],
                value: Math.round(value * 100) / 100
            });
        }
        return data;
    };
    
    return {
        stock_index: {
            items: {
                'KOSPI': { name: 'KOSPI', current: 2650.32, previous: 2640.15, change: 10.17, change_percent: 0.39, data: generateData(2600, 50, 365) },
                'KOSDAQ': { name: 'KOSDAQ', current: 820.45, previous: 815.20, change: 5.25, change_percent: 0.64, data: generateData(800, 20, 365) },
                'S&P500': { name: 'S&P 500', current: 5890.12, previous: 5875.30, change: 14.82, change_percent: 0.25, data: generateData(5800, 80, 365) },
                'NASDAQ': { name: 'NASDAQ', current: 19250.50, previous: 19180.20, change: 70.30, change_percent: 0.37, data: generateData(19000, 200, 365) },
                'Nikkei': { name: 'Nikkei 225', current: 38500.00, previous: 38420.00, change: 80.00, change_percent: 0.21, data: generateData(38000, 300, 365) },
            }
        },
        exchange_rate: {
            items: {
                'USD': { name: 'USD/KRW', current: 1432.50, previous: 1428.20, change: 4.30, change_percent: 0.30, data: generateData(1420, 15, 365) },
                'EUR': { name: 'EUR/KRW', current: 1485.30, previous: 1480.50, change: 4.80, change_percent: 0.32, data: generateData(1470, 20, 365) },
                'JPY': { name: 'JPY100/KRW', current: 925.00, previous: 920.00, change: 5.00, change_percent: 0.54, data: generateData(910, 15, 365) },
                'CNY': { name: 'CNY/KRW', current: 196.50, previous: 195.80, change: 0.70, change_percent: 0.36, data: generateData(195, 3, 365) },
                'GBP': { name: 'GBP/KRW', current: 1780.00, previous: 1775.00, change: 5.00, change_percent: 0.28, data: generateData(1770, 25, 365) },
            }
        },
        interest_rate: {
            items: {
                'KR': { name: '한국', current: 3.00, previous: 3.00, change: 0, change_percent: 0, data: generateData(3.0, 0.1, 365) },
                'US': { name: '미국', current: 4.50, previous: 4.50, change: 0, change_percent: 0, data: generateData(4.5, 0.1, 365) },
                'EU': { name: 'EU', current: 3.00, previous: 3.00, change: 0, change_percent: 0, data: generateData(3.0, 0.1, 365) },
                'JP': { name: '일본', current: 0.25, previous: 0.25, change: 0, change_percent: 0, data: generateData(0.25, 0.05, 365) },
                'CN': { name: '중국', current: 3.45, previous: 3.45, change: 0, change_percent: 0, data: generateData(3.45, 0.1, 365) },
            }
        }
    };
}

/**
 * Render Summary (Header Stats)
 */
function renderSummary() {
    const data = state.newsData;
    if (!data) return;
    
    document.getElementById('total-count').textContent = data.total || 0;
    document.getElementById('kr-count').textContent = data.kr_count || 0;
    document.getElementById('global-count').textContent = data.global_count || 0;
}

/**
 * Render Economic Ticker
 */
function renderTicker() {
    const track = document.getElementById('ticker-track');
    if (!track || !state.economicData) return;
    
    const items = [];
    
    // Stock indices
    const stocks = state.economicData.stock_index?.items || {};
    Object.values(stocks).forEach(item => {
        items.push(createTickerItem(item.name, item.current, item.change, item.change_percent));
    });
    
    // Exchange rates
    const exchanges = state.economicData.exchange_rate?.items || {};
    Object.values(exchanges).forEach(item => {
        items.push(createTickerItem(item.name, item.current, item.change, item.change_percent));
    });
    
    // Interest rates
    const interests = state.economicData.interest_rate?.items || {};
    Object.values(interests).forEach(item => {
        items.push(createTickerItem(item.name, item.current + '%', item.change, item.change_percent, true));
    });
    
    // Duplicate for seamless loop
    track.innerHTML = items.join('') + items.join('');
}

function createTickerItem(label, value, change, changePercent, isRate = false) {
    const changeClass = change > 0 ? 'up' : change < 0 ? 'down' : 'neutral';
    const changeSymbol = change > 0 ? '▲' : change < 0 ? '▼' : '';
    const formattedChange = isRate ? change.toFixed(2) + '%p' : (change >= 0 ? '+' : '') + change.toFixed(2);
    
    return `
        <div class="ticker-item">
            <span class="ticker-label">${label}</span>
            <span class="ticker-value">${typeof value === 'number' ? value.toLocaleString() : value}</span>
            <span class="ticker-change ${changeClass}">${changeSymbol} ${formattedChange} (${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}%)</span>
        </div>
    `;
}

/**
 * Render Distribution Bars (Category & Country)
 */
function renderDistributionBars() {
    renderCategoryBar();
    renderCountryBar();
    renderSentimentBar();
}

function renderCategoryBar() {
    const categories = state.newsData?.categories || {};
    const total = Object.values(categories).reduce((a, b) => a + b, 0);
    
    if (total === 0) return;
    
    const barContainer = document.getElementById('category-bar');
    const legendContainer = document.getElementById('category-legend');
    
    if (!barContainer || !legendContainer) return;
    
    // Render bar segments
    let barHtml = '';
    Object.entries(categories).forEach(([cat, count]) => {
        if (count === 0) return;
        const percent = (count / total * 100).toFixed(1);
        const color = CATEGORY_COLORS[cat] || '#6b7280';
        barHtml += `
            <div class="distribution-segment" 
                 style="width: ${percent}%; background-color: ${color};"
                 data-category="${cat}"
                 title="${cat}: ${count} (${percent}%)">
                <span>${percent}%</span>
            </div>
        `;
    });
    barContainer.innerHTML = barHtml;
    
    // Render legend
    let legendHtml = '';
    Object.entries(categories).forEach(([cat, count]) => {
        if (count === 0) return;
        const percent = (count / total * 100).toFixed(1);
        const color = CATEGORY_COLORS[cat] || '#6b7280';
        legendHtml += `
            <div class="legend-item" data-category="${cat}">
                <span class="legend-dot" style="background-color: ${color};"></span>
                <span class="legend-label">${cat}</span>
                <span class="legend-value">${count} (${percent}%)</span>
            </div>
        `;
    });
    legendContainer.innerHTML = legendHtml;
}

function renderCountryBar() {
    const countries = state.mapData?.countries || [];
    if (countries.length === 0) return;
    
    const barContainer = document.getElementById('country-bar');
    const legendContainer = document.getElementById('country-legend');
    
    if (!barContainer || !legendContainer) return;
    
    // Get top 5 countries
    const topCountries = countries.slice(0, 5);
    const othersCount = countries.slice(5).reduce((sum, c) => sum + c.count, 0);
    const total = countries.reduce((sum, c) => sum + c.count, 0);
    
    // Fallback colors for countries not in the map
    const fallbackColors = ['#f97316', '#06b6d4', '#a855f7', '#ec4899', '#84cc16'];
    
    // Render bar segments
    let barHtml = '';
    
    topCountries.forEach((country, idx) => {
        const percent = (country.count / total * 100).toFixed(1);
        const color = COUNTRY_COLORS[country.code] || fallbackColors[idx % fallbackColors.length];
        barHtml += `
            <div class="distribution-segment" 
                 style="width: ${percent}%; background-color: ${color};"
                 data-country="${country.code}"
                 title="${country.code}: ${country.count} (${percent}%)">
                <span>${percent}%</span>
            </div>
        `;
    });
    
    if (othersCount > 0) {
        const percent = (othersCount / total * 100).toFixed(1);
        barHtml += `
            <div class="distribution-segment" 
                 style="width: ${percent}%; background-color: ${COUNTRY_COLORS.Others};"
                 title="Others: ${othersCount} (${percent}%)">
                <span>${percent}%</span>
            </div>
        `;
    }
    
    barContainer.innerHTML = barHtml;
    
    // Render legend
    let legendHtml = '';
    topCountries.forEach((country, idx) => {
        const percent = (country.count / total * 100).toFixed(1);
        const color = COUNTRY_COLORS[country.code] || fallbackColors[idx % fallbackColors.length];
        legendHtml += `
            <div class="legend-item" data-country="${country.code}">
                <span class="legend-dot" style="background-color: ${color};"></span>
                <span class="legend-label">${country.code}</span>
                <span class="legend-value">${country.count} (${percent}%)</span>
            </div>
        `;
    });
    
    if (othersCount > 0) {
        const percent = (othersCount / total * 100).toFixed(1);
        legendHtml += `
            <div class="legend-item">
                <span class="legend-dot" style="background-color: ${COUNTRY_COLORS.Others};"></span>
                <span class="legend-label">Others</span>
                <span class="legend-value">${othersCount} (${percent}%)</span>
            </div>
        `;
    }
    
    legendContainer.innerHTML = legendHtml;
}

function renderSentimentBar() {
    const articles = state.newsData?.articles || [];
    if (articles.length === 0) return;
    
    const barContainer = document.getElementById('sentiment-bar');
    const legendContainer = document.getElementById('sentiment-legend');
    
    if (!barContainer || !legendContainer) return;
    
    // Count sentiments
    const sentimentCounts = { positive: 0, neutral: 0, negative: 0 };
    articles.forEach(article => {
        const sentiment = article.sentiment || 'neutral';
        if (sentimentCounts[sentiment] !== undefined) {
            sentimentCounts[sentiment]++;
        } else {
            sentimentCounts.neutral++;
        }
    });
    
    const total = articles.length;
    
    // Sentiment labels
    const sentimentLabels = {
        positive: '😊 긍정',
        neutral: '😐 중립',
        negative: '😟 부정',
    };
    
    // Render bar segments
    let barHtml = '';
    Object.entries(sentimentCounts).forEach(([sentiment, count]) => {
        if (count === 0) return;
        const percent = (count / total * 100).toFixed(1);
        const color = SENTIMENT_COLORS[sentiment];
        barHtml += `
            <div class="distribution-segment" 
                 style="width: ${percent}%; background-color: ${color};"
                 data-sentiment="${sentiment}"
                 title="${sentimentLabels[sentiment]}: ${count} (${percent}%)">
                <span>${percent}%</span>
            </div>
        `;
    });
    barContainer.innerHTML = barHtml;
    
    // Render legend
    let legendHtml = '';
    Object.entries(sentimentCounts).forEach(([sentiment, count]) => {
        const percent = (count / total * 100).toFixed(1);
        const color = SENTIMENT_COLORS[sentiment];
        legendHtml += `
            <div class="legend-item" data-sentiment="${sentiment}">
                <span class="legend-dot" style="background-color: ${color};"></span>
                <span class="legend-label">${sentimentLabels[sentiment]}</span>
                <span class="legend-value">${count} (${percent}%)</span>
            </div>
        `;
    });
    legendContainer.innerHTML = legendHtml;
}

/**
 * Render Economic Section (Google Finance Style)
 */
function renderEconomicSection() {
    const type = state.currentEconomicType;
    let dataSource;
    
    switch (type) {
        case 'stock':
            dataSource = state.economicData?.stock_index?.items;
            break;
        case 'exchange':
            dataSource = state.economicData?.exchange_rate?.items;
            break;
        case 'interest':
            dataSource = state.economicData?.interest_rate?.items;
            break;
    }
    
    if (!dataSource) return;
    
    const items = Object.entries(dataSource);
    if (items.length === 0) return;
    
    // Set selected indicator (first one by default)
    if (!state.selectedIndicator || !dataSource[state.selectedIndicator]) {
        state.selectedIndicator = items[0][0];
    }
    
    const selected = dataSource[state.selectedIndicator];
    
    // Update main display
    document.getElementById('economic-label').textContent = selected.name;
    document.getElementById('economic-value').textContent = 
        type === 'interest' ? selected.current.toFixed(2) + '%' : selected.current.toLocaleString();
    
    const changeEl = document.getElementById('economic-change');
    const changeClass = selected.change > 0 ? 'up' : selected.change < 0 ? 'down' : 'neutral';
    const changeSymbol = selected.change > 0 ? '▲' : selected.change < 0 ? '▼' : '';
    changeEl.className = `economic-main-change ${changeClass}`;
    changeEl.textContent = `${changeSymbol} ${selected.change >= 0 ? '+' : ''}${selected.change.toFixed(2)} (${selected.change_percent >= 0 ? '+' : ''}${selected.change_percent.toFixed(2)}%)`;
    
    // Render mini cards
    renderEconomicMiniCards(items, dataSource);
    
    // Render chart
    renderEconomicChart(selected);
}

function renderEconomicMiniCards(items, dataSource) {
    const container = document.getElementById('economic-mini-list');
    if (!container) return;
    
    container.innerHTML = items.map(([key, item]) => {
        const isActive = key === state.selectedIndicator;
        const changeClass = item.change > 0 ? 'up' : item.change < 0 ? 'down' : 'neutral';
        const changeSymbol = item.change > 0 ? '▲' : item.change < 0 ? '▼' : '';
        
        return `
            <div class="economic-mini-card ${isActive ? 'active' : ''}" data-indicator="${key}">
                <div class="economic-mini-label">${item.name}</div>
                <div class="economic-mini-change ${changeClass}">
                    ${changeSymbol} ${item.change_percent >= 0 ? '+' : ''}${item.change_percent.toFixed(2)}%
                </div>
            </div>
        `;
    }).join('');
}

function renderEconomicChart(indicator) {
    const ctx = document.getElementById('economic-chart');
    if (!ctx || !indicator || !indicator.data) return;
    
    // Get period in days
    const periodDays = {
        '1M': 30,
        '3M': 90,
        '6M': 180,
        '1Y': 365
    };
    
    const requestedDays = periodDays[state.currentPeriod] || 30;
    const originalLength = indicator.data.length;
    
    // Use minimum of requested days and available data
    const daysToShow = Math.min(requestedDays, originalLength);
    let data = indicator.data.slice(-daysToShow);
    
    console.log(`📊 Chart: Period=${state.currentPeriod}, Requested=${requestedDays}days, Available=${originalLength}, Showing=${data.length}`);
    
    // If no data available, return
    if (data.length === 0) {
        console.warn('No data for chart');
        return;
    }
    
    const labels = data.map(d => formatChartDate(d.time, state.currentPeriod));
    const values = data.map(d => d.value);
    
    // Calculate Y-axis range with padding
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const range = maxValue - minValue;
    const padding = range * 0.1 || 1; // 10% padding, minimum 1
    const yMin = minValue - padding;
    const yMax = maxValue + padding;
    
    // Calculate step size for Y-axis (aim for 4-5 ticks)
    const stepSize = calculateNiceStepSize(range, 4);
    
    // X-axis max ticks based on period
    const xMaxTicks = state.currentPeriod === '1M' ? 6 : 
                      state.currentPeriod === '3M' ? 6 :
                      state.currentPeriod === '6M' ? 6 : 8;
    
    if (state.economicChart) state.economicChart.destroy();
    
    const gradient = ctx.getContext('2d').createLinearGradient(0, 0, 0, 180);
    gradient.addColorStop(0, 'rgba(99, 102, 241, 0.3)');
    gradient.addColorStop(1, 'rgba(99, 102, 241, 0)');
    
    state.economicChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: indicator.name,
                data: values,
                borderColor: '#6366f1',
                backgroundColor: gradient,
                tension: 0.4,
                fill: true,
                pointRadius: 0,
                pointHoverRadius: 4,
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#1a1a25',
                    titleColor: '#fff',
                    bodyColor: '#b0b0c0',
                    borderColor: '#3a3a4a',
                    borderWidth: 1,
                    displayColors: false,
                    callbacks: {
                        label: (ctx) => {
                            return `${indicator.name}: ${ctx.parsed.y.toLocaleString()}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { 
                        color: '#7a7a8a', 
                        font: { size: 10 },
                        maxTicksLimit: xMaxTicks,
                        autoSkip: true,
                        maxRotation: 0,
                    }
                },
                y: {
                    min: yMin,
                    max: yMax,
                    grid: { color: '#2a2a3a' },
                    ticks: { 
                        color: '#7a7a8a', 
                        font: { size: 10 },
                        stepSize: stepSize,
                        maxTicksLimit: 5,
                        callback: (value) => value.toLocaleString(),
                    }
                }
            }
        }
    });
}

/**
 * Calculate a nice step size for axis ticks
 */
function calculateNiceStepSize(range, targetTicks) {
    if (range === 0) return 1;
    
    const roughStep = range / targetTicks;
    const magnitude = Math.pow(10, Math.floor(Math.log10(roughStep)));
    const normalized = roughStep / magnitude;
    
    let niceStep;
    if (normalized <= 1) niceStep = 1;
    else if (normalized <= 2) niceStep = 2;
    else if (normalized <= 5) niceStep = 5;
    else niceStep = 10;
    
    return niceStep * magnitude;
}

function formatChartDate(dateStr, period) {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr; // Return as-is if invalid
    
    switch (period) {
        case '1M':
            return `${date.getMonth() + 1}/${date.getDate()}`;
        case '3M':
            return `${date.getMonth() + 1}/${date.getDate()}`;
        case '6M':
            return `${date.getMonth() + 1}/${date.getDate()}`;
        case '1Y':
            return `${date.getFullYear().toString().slice(2)}/${date.getMonth() + 1}`;
        default:
            return `${date.getMonth() + 1}/${date.getDate()}`;
    }
}

/**
 * Render WordCloud
 */
function renderWordcloud() {
    const canvas = document.getElementById('wordcloud-canvas');
    if (!canvas || !state.wordcloudData) return;
    
    const keywords = state.wordcloudData.keywords || [];
    if (keywords.length === 0) {
        canvas.parentElement.innerHTML = '<p style="color: var(--text-muted); text-align: center;">No keywords available</p>';
        return;
    }
    
    // Prepare word list for WordCloud2 (더 많은 키워드 표시)
    const maxCount = Math.max(...keywords.map(k => k.count));
    const wordList = keywords.slice(0, 80).map(kw => {
        // 최소 9px, 최대 26px (10% 확대)
        const size = Math.max(9, Math.min(26, (kw.count / maxCount) * 22 + 9));
        return [kw.text, size];
    });
    
    // Set canvas size (높이 증가로 더 많은 키워드 표시)
    canvas.width = canvas.parentElement.offsetWidth || 400;
    canvas.height = 320;
    
    // Clear canvas
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#16161f';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Render wordcloud
    WordCloud(canvas, {
        list: wordList,
        gridSize: 4,  // 더 촘촘하게
        weightFactor: 1.0,  // 가중치 축소
        fontFamily: 'Noto Sans KR, sans-serif',
        color: function() {
            const colors = ['#6366f1', '#818cf8', '#a78bfa', '#c4b5fd', '#3b82f6', '#60a5fa', '#10b981'];
            return colors[Math.floor(Math.random() * colors.length)];
        },
        backgroundColor: '#16161f',
        rotateRatio: 0.15,  // 회전 최소화 (긴 단어 가독성)
        shape: 'circle',
        ellipticity: 0.65,
        drawOutOfBound: false,  // 캔버스 밖으로 나가지 않도록
        shrinkToFit: true,  // 공간에 맞게 축소
    });
}

/**
 * Render Headlines with Insights Panel
 */
function renderHeadlines() {
    const container = document.getElementById('headlines-list');
    const insightsPanel = document.getElementById('insights-panel');
    if (!container) return;
    
    // Use headlines from headlines_data.json, fallback to top articles
    const headlines = state.headlinesData?.headlines || [];
    const articles = state.newsData?.articles || [];
    const topItems = headlines.length > 0 ? headlines.slice(0, 6) : articles.slice(0, 6);
    
    if (topItems.length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 20px;">No headlines available</p>';
        return;
    }
    
    container.innerHTML = topItems.map((item, idx) => {
        return `
            <a href="${escapeHtml(item.url)}" target="_blank" class="headline-item" data-headline-idx="${idx}">
                <div class="headline-title">${escapeHtml(item.title)}</div>
                <div class="headline-source">${escapeHtml(item.source_name)} • ${formatTime(item.published_at_utc)}</div>
            </a>
        `;
    }).join('');
    
    // Add hover event listeners for insights panel
    setupHeadlineHoverEvents();
}

/**
 * Setup hover events for headlines to show insights in panel
 */
function setupHeadlineHoverEvents() {
    const headlineItems = document.querySelectorAll('.headline-item[data-headline-idx]');
    const insightsPanel = document.getElementById('insights-panel');
    
    if (!insightsPanel) return;
    
    // Get headlines array from headlines_data.json
    const headlines = state.headlinesData?.headlines || [];
    
    headlineItems.forEach(item => {
        item.addEventListener('mouseenter', (e) => {
            const idx = parseInt(e.currentTarget.dataset.headlineIdx);
            const headline = headlines[idx];
            
            if (headline) {
                showInsights(headline, insightsPanel);
            }
        });
    });
    
    // Reset to placeholder when mouse leaves the headlines container
    const container = document.getElementById('headlines-list');
    container?.addEventListener('mouseleave', () => {
        resetInsightsPanel(insightsPanel);
    });
}

/**
 * Show insights in the panel
 */
function showInsights(headline, panel) {
    const hasInsights = headline.insights && 
        (headline.insights.trade || headline.insights.logistics || headline.insights.scm);
    
    if (!hasInsights) {
        panel.innerHTML = `
            <div class="insights-content">
                <div class="insights-header">
                    <span class="insights-header-icon">📰</span>
                    <span class="insights-header-title">${escapeHtml(headline.title)}</span>
                </div>
                <div class="insights-placeholder" style="height: auto; padding: 10px 0;">
                    시사점 분석 데이터가 없습니다
                </div>
            </div>
        `;
        return;
    }
    
    panel.innerHTML = `
        <div class="insights-content">
            <div class="insights-header">
                <span class="insights-header-icon">💡</span>
                <span class="insights-header-title">${escapeHtml(headline.title)}</span>
            </div>
            <div class="insights-list">
                ${headline.insights.trade ? `
                    <div class="insight-item">
                        <span class="insight-label">무역</span>
                        <span class="insight-text">${escapeHtml(headline.insights.trade)}</span>
                    </div>
                ` : ''}
                ${headline.insights.logistics ? `
                    <div class="insight-item">
                        <span class="insight-label">물류</span>
                        <span class="insight-text">${escapeHtml(headline.insights.logistics)}</span>
                    </div>
                ` : ''}
                ${headline.insights.scm ? `
                    <div class="insight-item">
                        <span class="insight-label">SCM</span>
                        <span class="insight-text">${escapeHtml(headline.insights.scm)}</span>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

/**
 * Reset insights panel to placeholder
 */
function resetInsightsPanel(panel) {
    if (!panel) return;
    panel.innerHTML = `
        <div class="insights-placeholder">
            <span>💡</span> 헤드라인에 마우스를 올리면 시사점이 표시됩니다
        </div>
    `;
}

/**
 * Initialize Map
 */
function initMap() {
    const mapContainer = document.getElementById('critical-map');
    if (!mapContainer) return;
    
    state.map = L.map('critical-map', {
        center: [20, 0],
        zoom: 2,
        zoomControl: true,
        attributionControl: false,
    });
    
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
    }).addTo(state.map);
    
    renderMapMarkers();
}

/**
 * Render Map Markers with Article List Popup
 */
function renderMapMarkers() {
    if (!state.map || !state.mapData) return;
    
    const countries = state.mapData.countries || [];
    
    const coords = {
        US: [39.8, -98.5], CN: [35.8, 104.1], KR: [36.5, 127.7], JP: [36.2, 138.2],
        DE: [51.1, 10.4], SG: [1.3, 103.8], TW: [23.7, 120.9], VN: [14.0, 108.2],
        IN: [20.5, 78.9], NL: [52.1, 5.2], GB: [55.3, -3.4], FR: [46.2, 2.2],
        RU: [61.5, 105.3], UA: [48.3, 31.1], IR: [32.4, 53.6], SA: [23.8, 45.0],
        AE: [23.4, 53.8], YE: [15.5, 48.5], PA: [8.5, -80.7], EG: [26.8, 30.8],
    };
    
    // Country name mapping
    const countryNames = {
        US: '미국', CN: '중국', KR: '한국', JP: '일본', DE: '독일', SG: '싱가포르',
        TW: '대만', VN: '베트남', IN: '인도', NL: '네덜란드', GB: '영국', FR: '프랑스',
        RU: '러시아', UA: '우크라이나', IR: '이란', SA: '사우디', AE: 'UAE', YE: '예멘',
        PA: '파나마', EG: '이집트',
    };
    
    countries.forEach(country => {
        const coord = coords[country.code];
        if (!coord) return;
        
        const color = country.risk_level === 'high' ? '#ef4444' : 
                      country.risk_level === 'medium' ? '#f59e0b' : '#fbbf24';
        
        const marker = L.circleMarker(coord, {
            radius: Math.min(8 + country.count * 2, 20),
            fillColor: color,
            color: color,
            weight: 1,
            opacity: 0.8,
            fillOpacity: 0.5,
        }).addTo(state.map);
        
        // Build article list HTML
        const articles = country.articles || [];
        const articlesHtml = articles.length > 0 
            ? articles.map(article => `
                <a href="${escapeHtml(article.url)}" target="_blank" class="map-popup-article">
                    <div class="map-popup-article-title">${escapeHtml(article.title)}</div>
                    <div class="map-popup-article-source">${escapeHtml(article.source || '')}</div>
                </a>
            `).join('')
            : '<p style="color: #7a7a8a; font-size: 11px; text-align: center;">No articles available</p>';
        
        const popupContent = `
            <div class="map-popup">
                <div class="map-popup-header">
                    <span class="map-popup-country">${countryNames[country.code] || country.code} (${country.code})</span>
                    <span class="map-popup-count">🚨 ${country.count}건</span>
                </div>
                <div class="map-popup-articles">
                    ${articlesHtml}
                </div>
            </div>
        `;
        
        marker.bindPopup(popupContent, {
            maxWidth: 300,
            minWidth: 250,
        });
    });
}

/**
 * Render News List with Category Colors
 */
function renderNewsList() {
    const container = document.getElementById('news-list');
    if (!container) return;
    
    let articles = state.newsData?.articles || [];
    
    // Apply filters
    if (state.currentFilter !== 'all') {
        articles = articles.filter(a => a.news_type === state.currentFilter);
    }
    
    if (state.currentCategory) {
        articles = articles.filter(a => a.category === state.currentCategory);
    }
    
    // Apply sentiment filter
    if (state.currentSentiment) {
        articles = articles.filter(a => (a.sentiment || 'neutral') === state.currentSentiment);
    }
    
    // Pagination
    const totalPages = Math.ceil(articles.length / state.itemsPerPage);
    const startIdx = (state.currentPage - 1) * state.itemsPerPage;
    const pageArticles = articles.slice(startIdx, startIdx + state.itemsPerPage);
    
    if (pageArticles.length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted); text-align: center; padding: 40px;">No articles found</p>';
        renderPagination(0);
        return;
    }
    
    container.innerHTML = pageArticles.map(article => {
        // Sentiment badge logic
        const sentiment = article.sentiment || 'neutral';
        const sentimentLabel = sentiment === 'positive' ? '긍정' : 
                               sentiment === 'negative' ? '부정' : '중립';
        const sentimentIcon = sentiment === 'positive' ? '😊' : 
                              sentiment === 'negative' ? '😟' : '😐';
        
        return `
            <article class="news-card" data-category="${article.category}">
                <div class="news-card-header">
                    <h4 class="news-title">
                        <a href="${escapeHtml(article.url)}" target="_blank">${escapeHtml(article.title)}</a>
                    </h4>
                    <div class="news-badges">
                        <span class="badge badge-${sentiment}">${sentimentIcon} ${sentimentLabel}</span>
                        <span class="badge badge-${article.news_type.toLowerCase()}">${article.news_type === 'KR' ? '🇰🇷 Korea' : '🌍 Global'}</span>
                        <span class="badge badge-${article.category.toLowerCase()}">${article.category}</span>
                    </div>
                </div>
                <p class="news-summary">${escapeHtml(article.content_summary || '')}</p>
                <div class="news-footer">
                    <div class="news-meta">
                        <span>📰 ${escapeHtml(article.source_name)}</span>
                        <span>🕐 ${formatTime(article.published_at_utc)}</span>
                    </div>
                    <div class="news-tags">
                        ${(article.keywords || []).slice(0, 3).map(kw => 
                            `<span class="keyword-tag">${escapeHtml(kw)}</span>`
                        ).join(' ')}
                        ${(article.country_tags || []).slice(0, 2).map(tag => 
                            `<span class="country-tag">${escapeHtml(tag)}</span>`
                        ).join(' ')}
                    </div>
                </div>
            </article>
        `;
    }).join('');
    
    renderPagination(totalPages);
}

/**
 * Render Pagination
 */
function renderPagination(totalPages) {
    const container = document.getElementById('pagination');
    if (!container) return;
    
    if (totalPages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let html = '';
    
    html += `<button ${state.currentPage === 1 ? 'disabled' : ''} data-page="${state.currentPage - 1}">‹</button>`;
    
    const maxPages = 5;
    let startPage = Math.max(1, state.currentPage - Math.floor(maxPages / 2));
    let endPage = Math.min(totalPages, startPage + maxPages - 1);
    
    if (endPage - startPage < maxPages - 1) {
        startPage = Math.max(1, endPage - maxPages + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="${i === state.currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
    }
    
    html += `<button ${state.currentPage === totalPages ? 'disabled' : ''} data-page="${state.currentPage + 1}">›</button>`;
    
    container.innerHTML = html;
}

/**
 * Event Listeners
 */
function setupEventListeners() {
    // Filter tabs
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
            state.currentFilter = e.target.dataset.filter;
            state.currentPage = 1;
            renderNewsList();
        });
    });
    
    // Category chips (only for category filters, not sentiment)
    document.querySelectorAll('.filter-chip[data-category]').forEach(chip => {
        chip.addEventListener('click', (e) => {
            const category = e.target.dataset.category;
            
            if (state.currentCategory === category) {
                state.currentCategory = null;
                e.target.classList.remove('active');
            } else {
                document.querySelectorAll('.filter-chip[data-category]').forEach(c => c.classList.remove('active'));
                e.target.classList.add('active');
                state.currentCategory = category;
            }
            
            state.currentPage = 1;
            renderNewsList();
        });
    });
    
    // Sentiment chips
    document.querySelectorAll('.filter-chip[data-sentiment]').forEach(chip => {
        chip.addEventListener('click', (e) => {
            const sentiment = e.target.dataset.sentiment;
            
            if (state.currentSentiment === sentiment) {
                state.currentSentiment = null;
                e.target.classList.remove('active');
            } else {
                document.querySelectorAll('.filter-chip[data-sentiment]').forEach(c => c.classList.remove('active'));
                e.target.classList.add('active');
                state.currentSentiment = sentiment;
            }
            
            state.currentPage = 1;
            renderNewsList();
        });
    });
    
    // Economic tabs
    document.querySelectorAll('.economic-tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            document.querySelectorAll('.economic-tab').forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
            state.currentEconomicType = e.target.dataset.type;
            state.selectedIndicator = null; // Reset to first indicator
            renderEconomicSection();
        });
    });
    
    // Period tabs
    document.querySelectorAll('.period-tab').forEach(tab => {
        tab.addEventListener('click', (e) => {
            document.querySelectorAll('.period-tab').forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
            state.currentPeriod = e.target.dataset.period;
            renderEconomicSection();
        });
    });
    
    // Economic mini cards (delegated)
    document.getElementById('economic-mini-list')?.addEventListener('click', (e) => {
        const card = e.target.closest('.economic-mini-card');
        if (card) {
            state.selectedIndicator = card.dataset.indicator;
            renderEconomicSection();
        }
    });
    
    // Distribution legend items (category filter)
    document.getElementById('category-legend')?.addEventListener('click', (e) => {
        const item = e.target.closest('.legend-item');
        if (item) {
            const category = item.dataset.category;
            if (category) {
                // Toggle category filter
                if (state.currentCategory === category) {
                    state.currentCategory = null;
                    document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
                } else {
                    state.currentCategory = category;
                    document.querySelectorAll('.filter-chip').forEach(c => {
                        c.classList.toggle('active', c.dataset.category === category);
                    });
                }
                state.currentPage = 1;
                renderNewsList();
            }
        }
    });
    
    // Pagination
    document.getElementById('pagination')?.addEventListener('click', (e) => {
        if (e.target.tagName === 'BUTTON' && e.target.dataset.page) {
            state.currentPage = parseInt(e.target.dataset.page);
            renderNewsList();
            document.querySelector('.news-list')?.scrollIntoView({ behavior: 'smooth' });
        }
    });
}

/**
 * Utility Functions
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDateTime(dateStr) {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        return date.toLocaleString('ko-KR', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        });
    } catch {
        return dateStr;
    }
}

function formatTime(dateStr) {
    if (!dateStr) return '';
    try {
        const date = new Date(dateStr);
        const now = new Date();
        const diff = now - date;
        
        // 60분 이하: X분 전
        if (diff < 3600000) {
            const mins = Math.floor(diff / 60000);
            return `${mins}분 전`;
        } 
        // 60분 초과 ~ 24시간: X시간 Y분 전
        else if (diff < 86400000) {
            const hours = Math.floor(diff / 3600000);
            const mins = Math.floor((diff % 3600000) / 60000);
            if (mins > 0) {
                return `${hours}시간 ${mins}분 전`;
            }
            return `${hours}시간 전`;
        } 
        // 24시간 초과 ~ 7일: X일 전
        else if (diff < 604800000) {
            const days = Math.floor(diff / 86400000);
            return `${days}일 전`;
        } 
        // 7일 초과: 절대 시간
        else {
            return date.toLocaleDateString('ko-KR');
        }
    } catch {
        return dateStr;
    }
}

function showError(message) {
    const container = document.querySelector('.main-container');
    if (container) {
        container.innerHTML = `
            <div class="card" style="text-align: center; padding: 40px;">
                <p style="color: var(--danger); font-size: 18px;">⚠️ ${escapeHtml(message)}</p>
                <button onclick="location.reload()" style="margin-top: 16px; padding: 10px 20px; background: var(--accent-primary); color: white; border: none; border-radius: 8px; cursor: pointer;">
                    Retry
                </button>
            </div>
        `;
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', init);
