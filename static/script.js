
/*
const bibleData = {
    "Genesis": 50, "Exodus": 40, "Leviticus": 27, "Numbers": 36, "Deuteronomy": 34, 
    "Joshua": 24, "Judges": 21, "Ruth": 4, "1 Samuel": 31, "2 Samuel": 24,
    "1 Kings": 22, "2 Kings": 25, "1 Chronicles": 29, "2 Chronicles": 36, "Ezra": 10, 
    "Nehemiah": 13, "Esther": 10, "Job": 42, "Psalms": 150, "Proverbs": 31, 
    "Ecclesiastes": 12, "Song of Solomon": 8, "Isaiah": 66, "Jeremiah": 52, "Lamentations": 5,
    "Ezekiel": 48, "Daniel": 12, "Hosea": 14, "Joel": 3, "Amos": 9, "Obadiah": 1, 
    "Jonah": 4, "Micah": 7, "Nahum": 3, "Habakkuk": 3, "Zephaniah": 3, "Haggai": 2, 
    "Zechariah": 14, "Malachi": 4, "Matthew": 28, "Mark": 16, "Luke": 24, "John": 21, 
    "Acts": 28, "Romans": 16, "1 Corinthians": 16, "2 Corinthians": 13, "Galatians": 6, 
    "Ephesians": 6, "Philippians": 4, "Colossians": 4, "1 Thessalonians": 5, 
    "2 Thessalonians": 3, "1 Timothy": 6, "2 Timothy": 4, "Titus": 3, "Philemon": 1, 
    "Hebrews": 13, "James": 5, "1 Peter": 5, "2 Peter": 3, "1 John": 5, "2 John": 1, 
    "3 John": 1, "Jude": 1, "Revelation": 22
};
*/

let fullBibleData = {};  // will hold JSON data

// Fetch the verse data JSON (place it in static or serve via Flask)
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

document.getElementById("findSimilarButton").addEventListener("click", function () {
    const book = document.getElementById("bookSelect").value;
    const chapter = document.getElementById("chapterSelect").value;
    const verse = document.getElementById("verseSelect").value;

    if (!book || !chapter || !verse) {
        alert("Please select a book, chapter, and verse before searching.");
        return;
    }

    else {
        sendId(book, chapter, verse);
    }
});

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
}

// Send response to the server
function sendId(book, chapter, verse) {
    const booknNames = Object.keys(fullBibleData);
    const bookId = booknNames.indexOf(book) +1;

    const id = bookId * 1000000 + chapter * 1000 + verse;

    fetch("/find_similar", {
        methods: ["POST"],
        body: JSON.stringify({ id: id })
    })
    .then(response => response.json())
    .then(data => {})
}