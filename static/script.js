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

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

console.log("THREE loaded:", THREE.REVISION);

// START OF LOADING BIBLE DATA AND POPULATING DROPDOWNS
let fullBibleData = {};  // will hold JSON data

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
// END OF LOADING BIBLE DATA AND POPULATING DROPDOWNS


// START OF VISUALIZATION
let scene, camera, renderer, controls, raycaster, mouse, tooltipSprite;

function initVisualization() {

    // get the container
    const container = document.getElementById('visualization');

    // Setup scene
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 2000);
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setClearColor('#f8f9ff');

    container.appendChild(renderer.domElement);

    const canvas = renderer.domElement;

    // Add lighting
    const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
    scene.add(ambientLight);

    // Add camera controls
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;

    // Create 3D tooltip mesh instead of sprite
    const tooltipCanvas = document.createElement('canvas');
    const tooltipContext = tooltipCanvas.getContext('2d');
    tooltipCanvas.width = 512;
    tooltipCanvas.height = 200;
    
    const tooltipTexture = new THREE.CanvasTexture(tooltipCanvas);
    tooltipTexture.minFilter = THREE.LinearFilter;
    tooltipTexture.magFilter = THREE.LinearFilter;
    
    // Create a plane geometry for the tooltip
    const tooltipGeometry = new THREE.PlaneGeometry(2, 0.8);
    const tooltipMaterial = new THREE.MeshBasicMaterial({ 
        map: tooltipTexture,
        transparent: true,
        side: THREE.DoubleSide,
        depthTest: true,
        depthWrite: false
    });
    
    tooltipSprite = new THREE.Mesh(tooltipGeometry, tooltipMaterial);
    tooltipSprite.visible = false;
    scene.add(tooltipSprite);

    function updateTooltip(text) {
        // Clear canvas
        tooltipContext.clearRect(0, 0, tooltipCanvas.width, tooltipCanvas.height);
        
        // Draw layered background for depth effect
        const padding = 25;
        const radius = 16;
        
        // Back layer (shadow/depth)
        tooltipContext.fillStyle = 'rgba(0, 0, 0, 0.4)';
        tooltipContext.beginPath();
        tooltipContext.roundRect(padding + 4, padding + 6, tooltipCanvas.width - padding*2, tooltipCanvas.height - padding*2, radius);
        tooltipContext.fill();
        
        // Middle layer (border glow)
        const glowGradient = tooltipContext.createLinearGradient(0, 0, 0, tooltipCanvas.height);
        glowGradient.addColorStop(0, 'rgba(96, 165, 250, 0.3)');
        glowGradient.addColorStop(1, 'rgba(59, 130, 246, 0.3)');
        
        tooltipContext.fillStyle = glowGradient;
        tooltipContext.beginPath();
        tooltipContext.roundRect(padding - 2, padding - 2, tooltipCanvas.width - padding*2 + 4, tooltipCanvas.height - padding*2 + 4, radius + 2);
        tooltipContext.fill();
        
        // Main background with gradient
        const bgGradient = tooltipContext.createLinearGradient(0, 0, 0, tooltipCanvas.height);
        bgGradient.addColorStop(0, 'rgba(25, 35, 55, 0.98)');
        bgGradient.addColorStop(0.5, 'rgba(20, 28, 45, 0.98)');
        bgGradient.addColorStop(1, 'rgba(15, 23, 40, 0.98)');
        
        tooltipContext.fillStyle = bgGradient;
        tooltipContext.beginPath();
        tooltipContext.roundRect(padding, padding, tooltipCanvas.width - padding*2, tooltipCanvas.height - padding*2, radius);
        tooltipContext.fill();
        
        // Add inner highlight for dimension
        tooltipContext.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        tooltipContext.lineWidth = 2;
        tooltipContext.beginPath();
        tooltipContext.roundRect(padding + 2, padding + 2, tooltipCanvas.width - padding*2 - 4, tooltipCanvas.height - padding*2 - 4, radius - 2);
        tooltipContext.stroke();
        
        // Split text into lines
        const lines = text.split('<br>');
        
        // Draw citation (first line) with subtle shadow
        tooltipContext.shadowColor = 'rgba(0, 0, 0, 0.5)';
        tooltipContext.shadowBlur = 8;
        tooltipContext.shadowOffsetX = 2;
        tooltipContext.shadowOffsetY = 2;
        
        tooltipContext.fillStyle = '#ffffff';
        tooltipContext.font = 'bold 36px Arial';
        tooltipContext.textAlign = 'center';
        tooltipContext.textBaseline = 'middle';
        tooltipContext.fillText(lines[0], tooltipCanvas.width/2, tooltipCanvas.height/2 - 20);
        
        // Draw similarity percentage with glow effect
        tooltipContext.shadowColor = 'rgba(96, 165, 250, 0.8)';
        tooltipContext.shadowBlur = 12;
        
        const percentGradient = tooltipContext.createLinearGradient(
            tooltipCanvas.width/2 - 100, 0, 
            tooltipCanvas.width/2 + 100, 0
        );
        percentGradient.addColorStop(0, '#60a5fa');
        percentGradient.addColorStop(0.5, '#93c5fd');
        percentGradient.addColorStop(1, '#60a5fa');
        
        tooltipContext.fillStyle = percentGradient;
        tooltipContext.font = 'bold 28px Arial';
        tooltipContext.fillText(lines[1], tooltipCanvas.width/2, tooltipCanvas.height/2 + 25);
        
        // Reset shadow
        tooltipContext.shadowColor = 'transparent';
        tooltipContext.shadowBlur = 0;
        
        tooltipTexture.needsUpdate = true;
    }

    // Animation loop
    function animate() {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }
    animate();

    // Handle window resize
    window.addEventListener('resize', () => {
        const width = container.clientWidth;
        const height = container.clientHeight;
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height);
    });

    // Handle mouse interactions
    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2();

    
    canvas.addEventListener('mousemove', function (event) {
        const rect = canvas.getBoundingClientRect();
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        raycaster.setFromCamera(mouse, camera);
        const intersects = raycaster.intersectObjects(scene.children);

        const point = intersects.find(p => p.object.userData.citation);
        if (point) {
            const data = point.object.userData;
            const tooltipText = `${data.citation}<br>${(data.similarity * 100).toFixed(1)}% Similar`;
            updateTooltip(tooltipText);
            
            tooltipSprite.visible = true;
            tooltipSprite.position.copy(point.object.position);
            tooltipSprite.position.y += 0.5; // Position above the sphere
            
            // Make tooltip face the camera for better readability
            tooltipSprite.lookAt(camera.position);
            
            // Add slight tilt for depth
            tooltipSprite.rotation.x += 0.1;
        } else {
            tooltipSprite.visible = false;
        }
    });

    // Hide tooltip when mouse leaves canvas
    canvas.addEventListener('mouseout', function() {
        tooltipSprite.visible = false;
    });
}

function plotVerses(results) {
    // Clear previous scene except lights and tooltip
    const objectsToRemove = scene.children.filter(child => 
        child.type !== 'AmbientLight' && 
        (child.type !== 'Mesh' || child.geometry.type !== 'PlaneGeometry')
    );
    objectsToRemove.forEach(obj => scene.remove(obj));
    
    const center = results[0].coordinates;

    let maxDistance = 0;

    let minSimilarity = 0;

    results.forEach(verse => {
        if (verse.similarity < minSimilarity) {
            minSimilarity = verse.similarity;
        }
    });

    results.forEach((verse, index) => {

        const geometry = new THREE.SphereGeometry(0.05, 16, 16);

        const similarity = verse.similarity; // value between 0 and 1
        const base = new THREE.Color("#007BFF"); // blue
        const neutral = new THREE.Color("#AAAAAA"); // gray

        // Normalize similarity to range [0, 1]
        const normalized_similarity = (similarity - minSimilarity) / (1 - minSimilarity);

        // linear interpolation between blue and gray
        let color = neutral.clone().lerp(base, normalized_similarity); 

        const material = new THREE.MeshBasicMaterial({ color });
        const sphere = new THREE.Mesh(geometry, material);

        // Shift coordinates based on the first verse
        const shiftedX = verse.coordinates.x - center.x;
        const shiftedY = verse.coordinates.y - center.y;
        const shiftedZ = verse.coordinates.z - center.z;

        sphere.position.set(shiftedX, shiftedY, shiftedZ);
        sphere.userData = {citation: verse.citation, similarity: verse.similarity};
        scene.add(sphere);

        // Track bounding radius
        const dist = Math.sqrt(shiftedX**2 + shiftedY**2 + shiftedZ**2);
        if (dist > maxDistance) maxDistance = dist;
    });

    // Adjust camera distance dynamically
    camera.position.set(0, 0, maxDistance * 2); 
    camera.lookAt(0, 0, 0);
}

// END OF VISUALIZATION

// START OF FILLING IN SIMILARITY RESULTS

function fillSimilarityResults(results) {
    const originalCitation = document.getElementById("originalCitation");
    const originalText = document.getElementById("originalText");
    const similarVersesList = document.getElementById("similarVersesList");

    // Get the original verse (first in the results array)
    const originalVerse = results[0];
    originalCitation.textContent = originalVerse.citation;
    originalText.textContent = originalVerse.text;

    // Clear previous similar verses
    similarVersesList.innerHTML = "";

    // Display similar verses (skip the first one as it's the original)
    for (let i = 1; i < results.length; i++) {
        const verse = results[i];
        const similarityPercentage = (verse.similarity * 100).toFixed(1);

        const verseCard = `
            <div class="col-md-6 mb-3">
                <div class="card h-100">
                    <div class="card-body">
                        <h5 class="card-title d-flex justify-content-between">
                            ${verse.citation}
                            <span class="badge bg-primary">${similarityPercentage}% Similar</span>
                        </h5>
                        <p class="card-text">${verse.text}</p>
                    </div>
                </div>
            </div>
        `;
        similarVersesList.innerHTML += verseCard;
    }
}

// END OF FILLING IN SIMILARITY RESULTS

// Send response to the server
function sendId(book, chapter, verse) {
    const booknNames = Object.keys(fullBibleData);
    const bookId = booknNames.indexOf(book) +1;

    // error of chapter and verse being a string
    chapter = Number(chapter)
    verse = Number(verse)

    const id = (bookId * 1000000) + (chapter * 1000) + verse;

    // Show loader
    const spinner = document.getElementById("loader")
    spinner.style.display = "block";

    // Hide previous results
    const resultsDiv = document.getElementById("similarityResults");
    resultsDiv.style.display = "none";

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

        fillSimilarityResults(data.results);
        plotVerses(data.results);

    })
    .catch(error => {
        console.error('Error:', error);
        alert('An error occurred while fetching similar verses.');
    })
    
    .finally(() => {
        // Hide loader
        spinner.style.display = "none";

        // Show results
        resultsDiv.style.display = "block";
    });
}



// START OF EVENT LISTENERS

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

// Initialize 3D visualization when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    initVisualization();
});

// END OF EVENT LISTENERS

