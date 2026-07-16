let allRepos = [];
let filteredRepos = [];
let currentCategory = 'All';
let visibleCount = 0;
const PAGE_SIZE = 60;

const DOM = {
    grid: document.getElementById('toolsGrid'),
    loading: document.getElementById('loading'),
    searchInput: document.getElementById('searchInput'),
    categoryFilters: document.getElementById('categoryFilters'),
    sortSelect: document.getElementById('sortSelect'),
    resultsInfo: document.getElementById('resultsInfo'),
    loadMore: document.getElementById('loadMore'),
    statTools: document.getElementById('statTools'),
    statCats: document.getElementById('statCats'),
};

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function formatCount(n) {
    return n.toLocaleString('en-US');
}

async function init() {
    try {
        // Slim, minified index emitted by the build (build_site) containing only
        // the fields this page renders. The full dataset lives in
        // data/processed_repos.json and is only needed by project pages.
        const response = await fetch('data/index.json');
        if (!response.ok) throw new Error('Failed to fetch data');
        allRepos = await response.json();
        filteredRepos = [...allRepos];

        setupStats();
        setupCategories();
        setupEventListeners();
        filterAndSort();
    } catch (error) {
        DOM.loading.innerHTML = `Error loading data: ${escapeHtml(error.message)}<br>Make sure you are running this through a local server.`;
        console.error(error);
    }
}

function setupStats() {
    const cats = new Set();
    allRepos.forEach(r => (r.categories || []).forEach(c => cats.add(c)));
    if (DOM.statTools) DOM.statTools.textContent = formatCount(allRepos.length);
    if (DOM.statCats) DOM.statCats.textContent = formatCount(cats.size);
}

function setupCategories() {
    const categories = new Set();
    allRepos.forEach(repo => {
        (repo.categories || []).forEach(cat => categories.add(cat));
    });

    const catArray = ['All', ...Array.from(categories).sort()];

    DOM.categoryFilters.innerHTML = catArray.map(cat =>
        `<button class="filter-btn ${cat === 'All' ? 'active' : ''}" data-cat="${escapeHtml(cat)}" aria-pressed="${cat === 'All'}">${escapeHtml(cat)}</button>`
    ).join('');

    DOM.categoryFilters.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            DOM.categoryFilters.querySelectorAll('.filter-btn').forEach(b => {
                b.classList.remove('active');
                b.setAttribute('aria-pressed', 'false');
            });
            e.target.classList.add('active');
            e.target.setAttribute('aria-pressed', 'true');
            currentCategory = e.target.dataset.cat;
            filterAndSort();
        });
    });
}

function setupEventListeners() {
    DOM.searchInput.addEventListener('input', () => filterAndSort());
    DOM.sortSelect.addEventListener('change', () => filterAndSort());
    DOM.loadMore.addEventListener('click', () => {
        visibleCount = Math.min(visibleCount + PAGE_SIZE, filteredRepos.length);
        renderCards();
    });
}

function filterAndSort() {
    const query = DOM.searchInput.value.toLowerCase().trim();
    const sortBy = DOM.sortSelect.value;

    filteredRepos = allRepos.filter(repo => {
        const matchesCat = currentCategory === 'All' || (repo.categories || []).includes(currentCategory);
        if (!matchesCat) return false;
        if (!query) return true;
        const searchStr = `${repo.name} ${repo.description || ''} ${(repo.tags || []).join(' ')} ${(repo.commercial_alternatives || []).join(' ')}`.toLowerCase();
        return searchStr.includes(query);
    });

    filteredRepos.sort((a, b) => {
        if (sortBy === 'score') {
            return b.score - a.score || b.stargazers_count - a.stargazers_count;
        } else if (sortBy === 'stars') {
            return b.stargazers_count - a.stargazers_count;
        } else if (sortBy === 'recent') {
            return new Date(b.updated_at) - new Date(a.updated_at);
        }
        return 0;
    });

    visibleCount = Math.min(PAGE_SIZE, filteredRepos.length);
    render();
}

function projectCard(repo, rank) {
    const alts = (repo.commercial_alternatives || []).map(alt =>
        `<span class="alt-tag">Replaces ${escapeHtml(alt)}</span>`
    ).join('');

    const tags = (repo.tags || []).slice(0, 4).map(tag =>
        `<span class="tag">${escapeHtml(tag)}</span>`
    ).join('');

    const date = new Date(repo.updated_at).toLocaleDateString();
    const stars = repo.stargazers_count >= 1000
        ? (repo.stargazers_count / 1000).toFixed(1) + 'k'
        : repo.stargazers_count;

    const projectPath = repo.path || null;
    const titleTag = projectPath
        ? `<a href="${escapeHtml(projectPath)}" class="card-title">${escapeHtml(repo.name)}</a>`
        : `<a href="${escapeHtml(repo.html_url)}" target="_blank" rel="noreferrer" class="card-title">${escapeHtml(repo.name)}</a>`;

    const rankLabel = typeof rank === 'number'
        ? `${String(rank).padStart(2, '0')} &middot; Score ${repo.score}/10`
        : `Score ${repo.score}/10`;

    return `
        <div class="card" role="listitem">
            <div class="rank">${rankLabel}</div>
            ${titleTag}
            <div class="card-desc">${escapeHtml(repo.description || 'No description provided.')}</div>
            <div class="card-meta">
                ${alts}
                ${tags}
            </div>
            <div class="card-footer">
                <a class="star-link" href="${escapeHtml(repo.html_url)}" target="_blank" rel="noreferrer" title="View on GitHub">&#9733; ${stars}</a>
                <span>Updated ${date}</span>
            </div>
        </div>
    `;
}

function renderCards() {
    const slice = filteredRepos.slice(0, visibleCount);
    DOM.grid.innerHTML = slice.map((repo, i) => projectCard(repo, i + 1)).join('');

    const remaining = filteredRepos.length - visibleCount;
    if (remaining > 0) {
        DOM.loadMore.hidden = false;
        DOM.loadMore.textContent = `Load more tools (${formatCount(remaining)} left)`;
    } else {
        DOM.loadMore.hidden = true;
    }
}

function render() {
    DOM.loading.style.display = 'none';

    if (filteredRepos.length === 0) {
        DOM.resultsInfo.textContent = '';
        DOM.loadMore.hidden = true;
        DOM.grid.innerHTML = `<div class="empty-state"><strong>No tools match your search.</strong>Try a different term or clear the category filter.</div>`;
        return;
    }

    DOM.resultsInfo.innerHTML = `Showing <span class="count">${formatCount(Math.min(visibleCount, filteredRepos.length))}</span> of <span class="count">${formatCount(filteredRepos.length)}</span> tools`;
    renderCards();
}

init();
