let allRepos = [];
let filteredRepos = [];
let currentCategory = 'All';

const DOM = {
    grid: document.getElementById('toolsGrid'),
    loading: document.getElementById('loading'),
    searchInput: document.getElementById('searchInput'),
    categoryFilters: document.getElementById('categoryFilters'),
    sortSelect: document.getElementById('sortSelect'),
    resultsInfo: document.getElementById('resultsInfo')
};

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

async function init() {
    try {
        const response = await fetch('data/processed_repos.json');
        if (!response.ok) throw new Error('Failed to fetch data');
        allRepos = await response.json();
        filteredRepos = [...allRepos];

        setupCategories();
        setupEventListeners();
        render();
    } catch (error) {
        DOM.loading.innerHTML = `Error loading data: ${escapeHtml(error.message)}<br>Make sure you are running this through a local server.`;
        console.error(error);
    }
}

function setupCategories() {
    const categories = new Set();
    allRepos.forEach(repo => {
        (repo.categories || []).forEach(cat => categories.add(cat));
    });

    const catArray = ['All', ...Array.from(categories).sort()];

    DOM.categoryFilters.innerHTML = catArray.map(cat =>
        `<button class="filter-btn ${cat === 'All' ? 'active' : ''}" data-cat="${escapeHtml(cat)}">${escapeHtml(cat)}</button>`
    ).join('');

    DOM.categoryFilters.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            DOM.categoryFilters.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            currentCategory = e.target.dataset.cat;
            filterAndSort();
        });
    });
}

function setupEventListeners() {
    DOM.searchInput.addEventListener('input', () => filterAndSort());
    DOM.sortSelect.addEventListener('change', () => filterAndSort());
}

function filterAndSort() {
    const query = DOM.searchInput.value.toLowerCase();
    const sortBy = DOM.sortSelect.value;

    filteredRepos = allRepos.filter(repo => {
        const matchesCat = currentCategory === 'All' || (repo.categories || []).includes(currentCategory);
        const searchStr = `${repo.name} ${repo.description || ''} ${(repo.tags || []).join(' ')} ${(repo.commercial_alternatives || []).join(' ')}`.toLowerCase();
        const matchesQuery = searchStr.includes(query);
        return matchesCat && matchesQuery;
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

    const projectPath = repo.project ? repo.project.path : null;
    const titleTag = projectPath
        ? `<a href="${escapeHtml(projectPath)}" class="card-title">${escapeHtml(repo.name)}</a>`
        : `<a href="${escapeHtml(repo.html_url)}" target="_blank" rel="noreferrer" class="card-title">${escapeHtml(repo.name)}</a>`;

    const rankLabel = typeof rank === 'number'
        ? `${String(rank).padStart(2, '0')} &middot; Score ${repo.score}/10`
        : `Score ${repo.score}/10`;

    return `
        <div class="card" role="listitem">
            <div class="rank">${rankLabel}</div>
            <div class="card-header">
                ${titleTag}
            </div>
            <div class="card-desc">${escapeHtml(repo.description || 'No description provided.')}</div>
            <div class="card-meta">
                ${alts}
                ${tags}
            </div>
            <div class="card-footer">
                <a class="star-link" href="${escapeHtml(repo.html_url)}" target="_blank" rel="noreferrer" title="View on GitHub">★ ${stars}</a>
                <span>Updated ${date}</span>
            </div>
        </div>
    `;
}

function render() {
    DOM.loading.style.display = 'none';
    DOM.resultsInfo.textContent = `Showing ${filteredRepos.length} tools`;

    if (filteredRepos.length === 0) {
        DOM.grid.innerHTML = '<div class="empty-state">No tools found matching your search.</div>';
        return;
    }

    const renderList = filteredRepos.slice(0, 200);

    DOM.grid.innerHTML = renderList.map((repo, i) => projectCard(repo, i + 1)).join('');

    if (filteredRepos.length > 200) {
         DOM.grid.innerHTML += `<div class="overflow-note">And ${filteredRepos.length - 200} more&hellip; (refine search to see them)</div>`;
    }
}

init();
