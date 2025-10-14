function getRandomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}
// Configuration
const SCALE_FACTOR = 100; // Scale up coordinates

const CAMERA_X = getRandomInt(400, 700);
const CAMERA_Y = getRandomInt(500, 700);
const CAMERA_Z = getRandomInt(800, 1000);

// Ultra-efficient data structure using TypedArrays
class VerseManager {
    constructor() {
        this.positions = null; // Float32Array
        this.colors = null; // Float32Array for RGB colors
        this.sizes = null; // Float32Array for point sizes
        this.ids = []; // Store verse IDs
        this.citations = [];
        this.texts = [];
        this.books = []; // Store book numbers
        this.idToIndex = new Map(); // Fast O(1) lookup: verse ID -> array index
        this.count = 0;
    }

    init(size) {
        this.positions = new Float32Array(size * 3);
        this.colors = new Float32Array(size * 3);
        this.sizes = new Float32Array(size);
        this.ids = new Array(size);
        this.citations = new Array(size);
        this.texts = new Array(size);
        this.books = new Array(size);
        this.idToIndex.clear();
        this.count = size;
    }

    setVerse(index, id, x, y, z, citation, text, book) {
        const i = index * 3;
        // Apply scaling factor
        this.positions[i] = x * SCALE_FACTOR;
        this.positions[i + 1] = y * SCALE_FACTOR;
        this.positions[i + 2] = z * SCALE_FACTOR;

        // Set color based on book (1-66)
        const color = this.getColorForBook(book);
        this.colors[i] = color.r;
        this.colors[i + 1] = color.g;
        this.colors[i + 2] = color.b;

        // Set default size (small for background verses)
        this.sizes[index] = 0.8;

        this.ids[index] = id;
        this.citations[index] = citation;
        this.texts[index] = text;
        this.books[index] = book;
        this.idToIndex.set(id, index); // Build fast lookup map
    }
    
    getColorForBook(book) {
        // Cool-toned galaxy: blue → purple → magenta (200° to 320°)
        // Avoids highlight colors: cyan (180°) and warm tones (0°-60°: red/orange/yellow)
        const hue = 200 + ((book - 1) / 65) * 120;  // Maps 66 books across 120° hue range

        // Medium saturation & luminosity for visible but elegant star colors
        return this.hslToRgb(hue, 0.5, 0.7);
    }
    
    hslToRgb(h, s, l) {
        const c = (1 - Math.abs(2 * l - 1)) * s;
        const x = c * (1 - Math.abs((h / 60) % 2 - 1));
        const m = l - c / 2;
        let r, g, b;
        
        if (h < 60) { r = c; g = x; b = 0; }
        else if (h < 120) { r = x; g = c; b = 0; }
        else if (h < 180) { r = 0; g = c; b = x; }
        else if (h < 240) { r = 0; g = x; b = c; }
        else if (h < 300) { r = x; g = 0; b = c; }
        else { r = c; g = 0; b = x; }
        
        return {
            r: r + m,
            g: g + m,
            b: b + m
        };
    }

    getVerse(index) {
        const i = index * 3;
        return {
            id: this.ids[index],
            x: this.positions[i],
            y: this.positions[i + 1],
            z: this.positions[i + 2],
            citation: this.citations[index],
            text: this.texts[index],
            book: this.books[index]
        };
    }
}

// Scene setup
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x000000); // Pure black for space
scene.fog = new THREE.FogExp2(0x000000, 0.00025); // Exponential fog for depth

const camera = new THREE.PerspectiveCamera(
    60,
    window.innerWidth / window.innerHeight,
    1,
    5000
);
camera.position.set(CAMERA_X, CAMERA_Y, CAMERA_Z);

const renderer = new THREE.WebGLRenderer({ 
    antialias: false,
    powerPreference: "high-performance"
});
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(1);
document.getElementById('canvas-container').appendChild(renderer.domElement);

// Minimal lighting
const ambientLight = new THREE.AmbientLight(0xffffff, 1.0);
scene.add(ambientLight);

// Verse manager
const verseManager = new VerseManager();

// Points system (much more efficient than spheres)
let pointsObject;
let pointsGeometry;
let pointsMaterial;

// Store highlighted verses
let highlightedVerses = new Set();
let originalColors = null; // Store original colors for reset
let originalSizes = null; // Store original sizes for reset
let verseSimilarities = new Map(); // Store similarity scores for currently highlighted verses (id -> similarity)

// Mouse interaction
const raycaster = new THREE.Raycaster();
raycaster.params.Points.threshold = 3; // Adjusted for star glow size
const mouse = new THREE.Vector2();
const tooltip = document.getElementById('tooltip');
let lastClickedIndex = -1;

// Camera controls
let isRotating = false;
let isPanning = false;
let previousMousePosition = { x: 0, y: 0 };
let cameraTarget = new THREE.Vector3(0, 0, 0);
// Calculate distance from position (CAMERA_X, CAMERA_Y, CAMERA_Z)
let cameraDistance = Math.sqrt(CAMERA_X * CAMERA_X + CAMERA_Y * CAMERA_Y + CAMERA_Z * CAMERA_Z);
// Calculate rotation angles from position
let cameraRotation = {
    theta: Math.atan2(CAMERA_Y, CAMERA_Z),
    phi: Math.asin(CAMERA_X / cameraDistance)
};

// Smooth camera movement
let targetCameraDistance = cameraDistance;
let targetCameraRotation = { theta: cameraRotation.theta, phi: cameraRotation.phi };
let targetCameraTarget = new THREE.Vector3(0, 0, 0);
const smoothingFactor = 0.15;

// Performance: throttle raycasting
let lastRaycastTime = 0;
const raycastThrottle = 100;

// Create star texture for galaxy appearance
function createStarTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');

    // Create radial gradient for star glow
    const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    gradient.addColorStop(0, 'rgba(255, 255, 255, 1)');
    gradient.addColorStop(0.2, 'rgba(255, 255, 255, 0.8)');
    gradient.addColorStop(0.4, 'rgba(255, 255, 255, 0.3)');
    gradient.addColorStop(0.7, 'rgba(255, 255, 255, 0.1)');
    gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 64, 64);

    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    return texture;
}

// Load data function
window.loadVerses = function(jsonData) {
    
    setTimeout(() => {
        // Clear existing data
        if (pointsObject) {
            scene.remove(pointsObject);
            if (pointsGeometry) pointsGeometry.dispose();
            if (pointsMaterial) pointsMaterial.dispose();
        }

        const count = jsonData.length;
        verseManager.init(count);

        // Populate data with scaling
        for (let i = 0; i < count; i++) {
            const item = jsonData[i];
            verseManager.setVerse(
                i,
                item.id || 0,
                item.coordinates.x || 0,
                item.coordinates.y || 0,
                item.coordinates.z || 0,
                item.citation || '',
                item.text || '',
                item.book || 1
            );
        }

        // Create Points geometry
        pointsGeometry = new THREE.BufferGeometry();
        pointsGeometry.setAttribute('position',
            new THREE.BufferAttribute(verseManager.positions, 3)
        );
        pointsGeometry.setAttribute('color',
            new THREE.BufferAttribute(verseManager.colors, 3)
        );
        pointsGeometry.setAttribute('size',
            new THREE.BufferAttribute(verseManager.sizes, 1)
        );

        // Create star-like shader material for galaxy appearance
        pointsMaterial = new THREE.ShaderMaterial({
            uniforms: {
                pointTexture: { value: createStarTexture() }
            },
            vertexShader: `
                attribute vec3 color;
                attribute float size;
                varying vec3 vColor;
                void main() {
                    vColor = color;
                    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
                    gl_PointSize = size * 4.0 * (300.0 / -mvPosition.z);
                    gl_Position = projectionMatrix * mvPosition;
                }
            `,
            fragmentShader: `
                uniform sampler2D pointTexture;
                varying vec3 vColor;
                void main() {
                    vec4 texColor = texture2D(pointTexture, gl_PointCoord);
                    gl_FragColor = vec4(vColor, 1.0) * texColor;
                }
            `,
            blending: THREE.AdditiveBlending,
            depthTest: true,
            depthWrite: false,
            transparent: true
        });

        // Create Points object
        pointsObject = new THREE.Points(pointsGeometry, pointsMaterial);
        scene.add(pointsObject);

    }, 100);
};

// Mouse events
renderer.domElement.addEventListener('mousedown', (e) => {
    e.preventDefault();
    if (e.button === 0) {
        isRotating = true;
    } else if (e.button === 2) {
        isPanning = true;
    }
    previousMousePosition = { x: e.clientX, y: e.clientY };
});

renderer.domElement.addEventListener('contextmenu', (e) => {
    e.preventDefault();
});

renderer.domElement.addEventListener('mousemove', (e) => {
    mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;

    if (isRotating) {
        const deltaX = e.clientX - previousMousePosition.x;
        const deltaY = e.clientY - previousMousePosition.y;

        targetCameraRotation.theta -= deltaX * 0.001;
        targetCameraRotation.phi += deltaY * 0.001;

        targetCameraRotation.phi = Math.max(-Math.PI / 2 + 0.1, Math.min(Math.PI / 2 - 0.1, targetCameraRotation.phi));

        previousMousePosition = { x: e.clientX, y: e.clientY };
    } else if (isPanning) {
        const deltaX = e.clientX - previousMousePosition.x;
        const deltaY = e.clientY - previousMousePosition.y;

        const panSpeed = targetCameraDistance * 0.001;

        const right = new THREE.Vector3();
        const up = new THREE.Vector3();
        camera.getWorldDirection(right);
        right.cross(camera.up).normalize();
        up.set(0, 1, 0);

        targetCameraTarget.add(right.multiplyScalar(-deltaX * panSpeed));
        targetCameraTarget.add(up.multiplyScalar(deltaY * panSpeed));

        previousMousePosition = { x: e.clientX, y: e.clientY };
    } else {
        const now = Date.now();
        if (now - lastRaycastTime > raycastThrottle) {
            updateHover();
            lastRaycastTime = now;
        }
    }
});

renderer.domElement.addEventListener('mouseup', (e) => {
    if (e.button === 0) {
        isRotating = false;
    } else if (e.button === 2) {
        isPanning = false;
    }
});

renderer.domElement.addEventListener('click', (e) => {
    if (!pointsObject || isRotating || isPanning) return;
    
    // Update mouse coordinates precisely
    mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
    
    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObject(pointsObject);
    
    if (intersects.length > 0) {
        // Get the closest intersection
        const pointIndex = intersects[0].index;
        
        // Debug: log the index to verify it's changing
        console.log('Clicked point index:', pointIndex);
        
        // Only update if it's a different point
        if (pointIndex !== lastClickedIndex) {
            lastClickedIndex = pointIndex;
            const verse = verseManager.getVerse(pointIndex);
            console.log('Verse data:', verse);
            showTooltip(e.clientX, e.clientY, verse);
        }
    } else {
        lastClickedIndex = -1;
        hideTooltip();
    }
});

renderer.domElement.addEventListener('wheel', (e) => {
    e.preventDefault();
    const delta = e.deltaY * 0.5;
    targetCameraDistance += delta;
    targetCameraDistance = Math.max(100, Math.min(4000, targetCameraDistance));
});

function updateHover() {
    if (!pointsObject) return;
    
    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObject(pointsObject);
    
    if (intersects.length > 0) {
        renderer.domElement.style.cursor = 'pointer';
    } else {
        renderer.domElement.style.cursor = 'default';
    }
}

function showTooltip(x, y, verse) {

    tooltip.querySelector('.citation').textContent = verse.citation;
    tooltip.querySelector('.verse').textContent = verse.text;

    // Show scaled coordinates (divided by scale factor to show original values)
    const origX = (verse.x).toFixed(2);
    const origY = (verse.y).toFixed(2);
    const origZ = (verse.z).toFixed(2);
    tooltip.querySelector('.coordinates').textContent =
        `Coordinates: (${origX}, ${origY}, ${origZ})`;

    // Show similarity score if this verse is highlighted
    const similarityElement = tooltip.querySelector('.similarity');
    if (verseSimilarities.has(verse.id)) {
        const similarity = verseSimilarities.get(verse.id);
        similarityElement.textContent = `Similarity: ${(similarity * 100).toFixed(1)}%`;
        similarityElement.style.display = 'block';
    } else {
        similarityElement.style.display = 'none';
    }

    tooltip.style.display = 'block';

    // Position tooltip to avoid going off screen
    const tooltipWidth = 400;
    const tooltipHeight = 150;
    let left = x + 15;
    let top = y + 15;

    if (left + tooltipWidth > window.innerWidth) {
        left = x - tooltipWidth - 15;
    }
    if (top + tooltipHeight > window.innerHeight) {
        top = y - tooltipHeight - 15;
    }

    tooltip.style.left = left + 'px';
    tooltip.style.top = top + 'px';
}

function hideTooltip() {
    tooltip.style.display = 'none';
}

// Update camera position with smooth interpolation
function updateCamera() {
    // Smooth interpolation for all camera parameters
    cameraDistance += (targetCameraDistance - cameraDistance) * smoothingFactor;
    cameraRotation.theta += (targetCameraRotation.theta - cameraRotation.theta) * smoothingFactor;
    cameraRotation.phi += (targetCameraRotation.phi - cameraRotation.phi) * smoothingFactor;
    cameraTarget.lerp(targetCameraTarget, smoothingFactor);

    const x = cameraDistance * Math.sin(cameraRotation.theta) * Math.cos(cameraRotation.phi);
    const y = cameraDistance * Math.sin(cameraRotation.phi);
    const z = cameraDistance * Math.cos(cameraRotation.theta) * Math.cos(cameraRotation.phi);

    camera.position.set(x, y, z).add(cameraTarget);
    camera.lookAt(cameraTarget);

    document.getElementById('x').textContent = (camera.position.x).toFixed(2);
    document.getElementById('y').textContent = (camera.position.y).toFixed(2);
    document.getElementById('z').textContent = (camera.position.z).toFixed(2);
}

// Animation loop
function animate() {
    requestAnimationFrame(animate);
    updateCamera();
    renderer.render(scene, camera);
}

// Handle window resize
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

// Start animation
animate();

// Load initial data
fetch('/api/verses')
    .then(response => response.json())
    .then(data => {
        console.log(data.verses[0])
        loadVerses(data.verses);
    })
    .catch(error => {
        console.error('Error loading file:', error);
        alert('Failed to load verses_3d.json');
    });

// Function to highlight similar verses
export function highlightSimilarVerses(similarVerses, originalVerseId = null) {
    if (!pointsObject || !verseManager.ids) {
        console.warn('Points not loaded yet');
        return;
    }

    // Store original colors and sizes if not already stored
    if (!originalColors) {
        originalColors = new Float32Array(verseManager.colors);
        originalSizes = new Float32Array(verseManager.sizes);
    } else {
        // Reset to original colors and sizes
        verseManager.colors.set(originalColors);
        verseManager.sizes.set(originalSizes);
    }

    // Clear previous highlights and similarities
    highlightedVerses.clear();
    verseSimilarities.clear();

    // Populate verseSimilarities map for tooltip access
    similarVerses.forEach(item => {
        verseSimilarities.set(item.id, item.similarity);
    });

    // Dim all non-highlighted verses (reduce brightness and size)
    for (let i = 0; i < verseManager.count; i++) {
        const colorIndex = i * 3;
        // Multiply colors by 0.3 to dim them
        verseManager.colors[colorIndex] = originalColors[colorIndex] * 0.5;
        verseManager.colors[colorIndex + 1] = originalColors[colorIndex + 1] * 0.5;
        verseManager.colors[colorIndex + 2] = originalColors[colorIndex + 2] * 0.5;
        // Set small size for all points
        verseManager.sizes[i] = 0.8;
    }

    // Highlight the original verse if provided (largest and brightest)
    if (originalVerseId !== null && verseManager.idToIndex.has(originalVerseId)) {
        const i = verseManager.idToIndex.get(originalVerseId);
        highlightedVerses.add(i);
        const colorIndex = i * 3;

        // Original verse: bright cyan/blue (0.0, 0.8, 1.0)
        verseManager.colors[colorIndex] = 0.0; // R
        verseManager.colors[colorIndex + 1] = 0.8; // G
        verseManager.colors[colorIndex + 2] = 1.0; // B

        // Make original verse the largest
        verseManager.sizes[i] = 5.0;
    }

    // Highlight the similar verses using efficient lookup
    similarVerses.forEach(item => {
        const verseId = item.id;
        const similarity = item.similarity;

        // Use fast O(1) lookup instead of O(n) loop
        if (verseManager.idToIndex.has(verseId)) {
            const i = verseManager.idToIndex.get(verseId);
            highlightedVerses.add(i);

            // Color based on similarity: high similarity = brighter/more intense
            // Use red-yellow gradient for highlighted verses
            const colorIndex = i * 3;

            // High similarity = bright yellow/white (1.0, 1.0, 0.2)
            // Low similarity = orange/red (1.0, 0.5, 0.0)
            verseManager.colors[colorIndex] = 1.0; // R
            verseManager.colors[colorIndex + 1] = 0.5 + (similarity * 0.5); // G (0.5 to 1.0)
            verseManager.colors[colorIndex + 2] = similarity * 0.3; // B (0 to 0.3)

            // Size based on similarity: higher similarity = larger size
            // Range from 3.0 (low similarity) to 4.5 (high similarity)
            verseManager.sizes[i] = 3.0 + (similarity * 1.5);
        }
    });

    // Update the colors and sizes in the geometry
    pointsGeometry.attributes.color.needsUpdate = true;
    pointsGeometry.attributes.size.needsUpdate = true;
}

// Export verseManager for use in other modules
export { verseManager };

// Function to clear highlights
export function clearHighlights() {
    if (!pointsObject || !originalColors || !originalSizes) {
        return;
    }

    // Reset to original colors and sizes
    verseManager.colors.set(originalColors);
    verseManager.sizes.set(originalSizes);
    pointsGeometry.attributes.color.needsUpdate = true;
    pointsGeometry.attributes.size.needsUpdate = true;
    highlightedVerses.clear();
    verseSimilarities.clear();

    console.log('Highlights cleared');
}

// Function to pan camera to highlighted verses
export function panCameraToVerses(similarVerses, originalVerseId = null) {
    if (!pointsObject || !verseManager.ids) {
        console.warn('Points not loaded yet');
        return;
    }

    // Focus on the original verse if provided, otherwise use centroid of similar verses
    let focusPoint;

    if (originalVerseId !== null && verseManager.idToIndex.has(originalVerseId)) {
        // Focus on the original verse that the user searched for
        const i = verseManager.idToIndex.get(originalVerseId);
        const idx = i * 3;
        focusPoint = {
            x: verseManager.positions[idx],
            y: verseManager.positions[idx + 1],
            z: verseManager.positions[idx + 2]
        };
        console.log(`Panning camera to original verse ID ${originalVerseId} at:`, focusPoint);
    } else {
        // Fallback: calculate centroid of similar verses
        const positions = [];
        similarVerses.forEach(item => {
            if (verseManager.idToIndex.has(item.id)) {
                const i = verseManager.idToIndex.get(item.id);
                const idx = i * 3;
                positions.push({
                    x: verseManager.positions[idx],
                    y: verseManager.positions[idx + 1],
                    z: verseManager.positions[idx + 2]
                });
            }
        });

        if (positions.length === 0) {
            console.warn('No verses found to pan to');
            return;
        }

        focusPoint = positions.reduce((acc, pos) => ({
            x: acc.x + pos.x / positions.length,
            y: acc.y + pos.y / positions.length,
            z: acc.z + pos.z / positions.length
        }), { x: 0, y: 0, z: 0 });
        console.log(`Panning camera to centroid of ${positions.length} similar verses at:`, focusPoint);
    }

    // Set camera target to the focus point
    targetCameraTarget.set(focusPoint.x, focusPoint.y, focusPoint.z);

    // Use a fixed comfortable viewing distance
    targetCameraDistance = 400;

    console.log(`Camera distance: ${targetCameraDistance}`);
}