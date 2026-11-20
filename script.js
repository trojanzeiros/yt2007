
const API = "/api";

const params = new URLSearchParams(window.location.search);
const videoId = params.get("v");

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

async function api(path) {
    const response = await fetch(API + path);

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || "API request failed");
    }

    return data;
}

function getId(video) {
    return video.id?.videoId || video.id;
}

function createVideo(video) {
    const snippet = video.snippet || {};
    const id = getId(video);

    const thumbnail =
        snippet.thumbnails?.medium?.url ||
        snippet.thumbnails?.default?.url || "";

    return `
        <article class="video-item">

            <a href="watch.html?v=${encodeURIComponent(id)}">
                <img
                    src="${escapeHTML(thumbnail)}"
                    alt="${escapeHTML(snippet.title)}"
                    loading="lazy"
                >
            </a>

            <div class="video-info">

                <h3>
                    <a href="watch.html?v=${encodeURIComponent(id)}">
                        ${escapeHTML(snippet.title)}
                    </a>
                </h3>

                <p>
                    ${escapeHTML(
                        (snippet.description || "").slice(0, 180)
                    )}
                </p>

                <small>
                    From: ${escapeHTML(snippet.channelTitle)}
                </small>

                <div class="stars">★★★★★</div>

            </div>

        </article>
    `;
}

async function loadVideos(query = "") {
    const list = document.getElementById("videoList");

    if (!list) return;

    list.innerHTML = "<p>Loading videos...</p>";

    try {
        const endpoint = query
            ? `/videos?q=${encodeURIComponent(query)}`
            : "/videos";

        const data = await api(endpoint);
        const videos = data.items || [];

        list.innerHTML = videos.length
            ? videos.map(createVideo).join("")
            : "<p>No videos found.</p>";

        const featured = document.getElementById("featuredStrip");

        if (featured) {
            featured.innerHTML = videos.slice(0, 6).map(video => {
                const snippet = video.snippet;
                const id = getId(video);

                const thumbnail =
                    snippet.thumbnails?.medium?.url ||
                    snippet.thumbnails?.default?.url || "";

                return `
                    <div class="featured-item">
                        <a href="watch.html?v=${encodeURIComponent(id)}">
                            <img
                                src="${escapeHTML(thumbnail)}"
                                alt=""
                            >
                            ${escapeHTML(snippet.title)}
                        </a>
                    </div>
                `;
            }).join("");
        }

    } catch (error) {
        list.innerHTML = `
            <div class="panel">
                Could not load videos:
                ${escapeHTML(error.message)}
            </div>
        `;
    }
}

async function loadWatch() {
    if (!document.getElementById("videoTitle")) return;

    if (!videoId) {
        document.getElementById("videoTitle").textContent =
            "Video not specified";
        return;
    }

    try {
        const data = await api(
            `/video/${encodeURIComponent(videoId)}`
        );

        const video = data.items?.[0];

        if (!video) {
            throw new Error("Video not found");
        }

        const snippet = video.snippet;
        const stats = video.statistics || {};

        document.title = snippet.title + " - YouTube";

        document.getElementById("videoTitle").textContent =
            snippet.title;

        document.getElementById("videoDescription").textContent =
            snippet.description || "";

        document.getElementById("videoViews").textContent =
            Number(stats.viewCount || 0).toLocaleString();

        document.getElementById("videoChannel").textContent =
            snippet.channelTitle;

        document.getElementById("youtubeLink").href =
            `https://www.youtube.com/watch?v=${encodeURIComponent(videoId)}`;

        const iframe = document.createElement("iframe");

        iframe.src =
            `https://www.youtube.com/embed/${encodeURIComponent(videoId)}?rel=0`;

        iframe.title = snippet.title;
        iframe.allow =
            "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";

        iframe.allowFullscreen = true;

        document.getElementById("player").replaceChildren(iframe);

        await loadRelated();

    } catch (error) {
        document.getElementById("videoTitle").textContent =
            "Unable to load video";

        document.getElementById("videoDescription").textContent =
            error.message;
    }
}

async function loadRelated() {
    const container = document.getElementById("relatedVideos");

    if (!container) return;

    try {
        const data = await api(
            `/related/${encodeURIComponent(videoId)}`
        );

        const videos = data.items || [];

        container.innerHTML = videos.map(video => {
            const snippet = video.snippet;
            const id = getId(video);

            return `
                <p>
                    <a href="watch.html?v=${encodeURIComponent(id)}">
                        ${escapeHTML(snippet.title)}
                    </a>
                </p>
            `;
        }).join("") || "No related videos.";

    } catch (error) {
        container.textContent = "Unable to load related videos.";
    }
}

const searchForm = document.getElementById("searchForm");

if (searchForm) {
    searchForm.addEventListener("submit", event => {
        event.preventDefault();

        const query = document
            .getElementById("searchInput")
            .value.trim();

        loadVideos(query);
    });
}

if (videoId) {
    loadWatch();
} else {
    loadVideos();
}
