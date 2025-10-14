// Import highlight and camera functions from 3d.js
import { highlightSimilarVerses, panCameraToVerse } from './3d.js';

// Landing overlay functionality
const landingOverlay = document.getElementById('landing-overlay');
const uiSections = document.querySelectorAll('.ui-section');

landingOverlay.addEventListener('click', function() {
    landingOverlay.classList.add('hidden');
    setTimeout(() => {
        uiSections.forEach(section => section.classList.add('visible'));
    }, 300);
});

// Toggle functionality
const slider = document.getElementById('slider');
const verseButton = document.getElementById('verseButton');
const textButton = document.getElementById('textButton');
const searchByVerse = document.getElementById('searchByVerse');
const searchByText = document.getElementById('searchByText');

function showVerseSearch() {
    verseButton.classList.add('active');
    textButton.classList.remove('active');
    slider.classList.remove('slide-right');
    searchByVerse.classList.add('active');
    searchByText.classList.remove('active');
}

function showTextSearch() {
    textButton.classList.add('active');
    verseButton.classList.remove('active');
    slider.classList.add('slide-right');
    searchByText.classList.add('active');
    searchByVerse.classList.remove('active');
}

textButton.addEventListener('click', showTextSearch);
verseButton.addEventListener('click', showVerseSearch);

// Polupate dropdowns
let fullBibleData = {};

fetch("/static/bible_data.json")
    .then(response => response.json())
    .then(data => {
        fullBibleData = data;
        populateBooks();
    });

// Populate Book Dropdown
function populateBooks() {
    const bookSelect = document.getElementById("bookSelect");
    Object.keys(fullBibleData).forEach(book => {
        const option = document.createElement("option");
        option.value = book;
        option.textContent = book;
        bookSelect.appendChild(option);
    });

    // Set the default book to the first one in the list
    bookSelect.selectedIndex = 0;  // Default to the first book
    const firstBook = bookSelect.value;
    populateChapters(firstBook);
}

// Populate Chapters
function populateChapters(book) {
    const chapterSelect = document.getElementById("chapterSelect");
    const verseSelect = document.getElementById("verseSelect");

    chapterSelect.innerHTML = "";  // Clear previous options
    verseSelect.innerHTML = "";     // Clear previous options

    const numChapters = fullBibleData[book].Chapters;

    for (let i = 1; i <= numChapters; i++) {
        const option = document.createElement("option");
        option.value = i;
        option.textContent = i;
        chapterSelect.appendChild(option);
    }

    // Set the default chapter to the first one
    chapterSelect.selectedIndex = 0;  // Default to the first chapter
    const firstChapter = chapterSelect.value;
    populateVerses(book, firstChapter);
}

// Populate Verses
function populateVerses(book, chapter) {
    const verseSelect = document.getElementById("verseSelect");

    verseSelect.innerHTML = "";  // Clear previous options

    const numVerses = fullBibleData[book].Verses[chapter];
    for (let i = 1; i <= numVerses; i++) {
        const option = document.createElement("option");
        option.value = i;
        option.textContent = i;
        verseSelect.appendChild(option);
    }

    verseSelect.selectedIndex = 0;
}

// Function to display verses in the results list
function displayVersesList(verses, originalVerse = null) {
    const resultsList = document.getElementById('results-list');
    resultsList.innerHTML = ''; // Clear previous results

    // Display original verse first if provided
    if (originalVerse !== null) {
        const verseItem = document.createElement('div');
        verseItem.className = 'verse-item original';
        verseItem.dataset.verseId = originalVerse.id;
        verseItem.innerHTML = `
            <div class="verse-citation">${originalVerse.citation}</div>
            <div class="verse-text">${originalVerse.text}</div>
            <div class="verse-similarity">Original Verse</div>
        `;
        // Add click handler to pan camera to this verse and super-emphasize it
        verseItem.addEventListener('click', () => {
            // Re-highlight with this verse super-emphasized (magenta, size 6.0)
            highlightSimilarVerses(verses, originalVerse.id, originalVerse.id);
            // Pan camera to zoom in on this verse
            panCameraToVerse(originalVerse.id);
        });
        resultsList.appendChild(verseItem);
    }

    // Display similar verses (verses already contain citation and text from API)
    verses.forEach(item => {
        const verseItem = document.createElement('div');
        verseItem.className = 'verse-item';
        verseItem.dataset.verseId = item.id;
        verseItem.innerHTML = `
            <div class="verse-citation">${item.citation}</div>
            <div class="verse-text">${item.text}</div>
            <div class="verse-similarity">Similarity: ${(item.similarity * 100).toFixed(1)}%</div>
        `;
        // Add click handler to pan camera to this verse and super-emphasize it
        verseItem.addEventListener('click', () => {
            // Re-highlight with this verse super-emphasized (magenta, size 6.0)
            // Keep original verse highlighted if it exists
            const origId = originalVerse ? originalVerse.id : null;
            highlightSimilarVerses(verses, origId, item.id);
            // Pan camera to zoom in on this verse
            panCameraToVerse(item.id);
        });
        resultsList.appendChild(verseItem);
    });
}

// Send verse to the server
function sendVerse(book, chapter, verse) {
    const booknNames = Object.keys(fullBibleData);
    const bookId = booknNames.indexOf(book) +1;

    // error of chapter and verse being a string
    chapter = Number(chapter)
    verse = Number(verse)

    const id = (bookId * 1000000) + (chapter * 1000) + verse;

    console.log(id)

    fetch("/find_similar", {
        method: "POST",
        body: JSON.stringify({ id: id }),
        headers: {"Content-Type": "application/json"}
    })

    // this handles the response that we receive from the server
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            return;
        }

        const originalVerse = data.original_verse;
        const similarVerses = data.results;

        // Display verses in the list with original verse data
        displayVersesList(similarVerses, originalVerse);

        // Highlight similar verses with the original verse ID
        highlightSimilarVerses(similarVerses, originalVerse.id);

        // Pan camera to centroid of all similar verses (overview)
        panCameraToVerse(similarVerses);
    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while fetching similar verses.');
    });
}

// Send text query to the server
function sendQuery(query) {
    const loadingSpinner = document.getElementById('searchLoadingSpinner');

    // Show loading spinner
    loadingSpinner.classList.add('active');

    fetch("/find_query", {
        method: "POST",
        body: JSON.stringify({ query: query }),
        headers: {"Content-Type": "application/json"}
    })
    .then(response => response.json())
    .then(data => {
        // Hide loading spinner
        loadingSpinner.classList.remove('active');

        if (data.error) {
            alert(data.error);
            return;
        }

        // Results already contain citation and text from API
        const similarVerses = data.results;

        // Display verses in the list (no original verse for text queries)
        displayVersesList(similarVerses, null);

        // Highlight similar verses (no original verse for text queries)
        highlightSimilarVerses(similarVerses, null);

        // Pan camera to centroid of all similar verses
        panCameraToVerse(similarVerses);
    })
    .catch(error => {
        // Hide loading spinner on error
        loadingSpinner.classList.remove('active');

        console.error('Error:', error);
        alert('An error occurred while fetching similar verses.');
    });
}

// Event Listeners
document.getElementById("bookSelect").addEventListener("change", function () {
    const book = this.value;
    populateChapters(book);
});

document.getElementById("chapterSelect").addEventListener("change", function () {
    const book = document.getElementById("bookSelect").value;
    const chapter = this.value;
    populateVerses(book, chapter);
});

document.getElementById("findByVerseButton").addEventListener("click", function () {
    const book = document.getElementById("bookSelect").value;
    const chapter = document.getElementById("chapterSelect").value;
    const verse = document.getElementById("verseSelect").value;

    if (!book || !chapter || !verse) {
        alert("Please select a book, chapter, and verse before searching.");
        return;
    }

    else {
        sendVerse(book, chapter, verse);
    }
});

document.getElementById("findByTextButton").addEventListener("click", function () {
    const query = document.getElementById("searchInput").value.trim();
    console.log(query)
    if (!query) {
        alert("Please enter a search query.");
        return;
    }
    
    else {
        sendQuery(query);   
    }
});