
HTML_3D_INDEX = """
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <title>3D Viewer (With Rotation & Zoom)</title>
  <!-- Bootstrap for layout & styling -->
  <link
    href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css\"
    rel=\"stylesheet\"
  />
  <!-- Three.js -->
  <script src=\"https://cdn.jsdelivr.net/npm/three@0.131.3/build/three.min.js\"></script>
  <!-- STL Loader -->
  <script src=\"https://cdn.jsdelivr.net/npm/three@0.131.3/examples/js/loaders/STLLoader.js\"></script>
  <!-- OrbitControls for rotation/zoom -->
  <script src=\"https://cdn.jsdelivr.net/npm/three@0.131.3/examples/js/controls/OrbitControls.js\"></script>

  <style>
    .model-container {
      width: 100%;
      height: 250px;
      border: 1px solid #ccc;
      margin-bottom: 20px;
      position: relative;
    }

    .model-title {
      position: absolute;
      top: 5px;
      left: 5px;
      background-color: rgba(255, 255, 255, 0.7);
      padding: 3px 6px;
      border-radius: 4px;
      font-size: 0.9rem;
      font-weight: 600;
    }

    .card {
      border: none;
      margin: 10px 0;
    }
  </style>
</head>
<body class=\"bg-light\">

  <div class=\"container py-4\">
    <h1 class=\"mb-4\">3D Parts Viewer</h1>
    <p class=\"mb-3\">
      Đây là trang chính, mỗi chi tiết STL được hiển thị trong khung riêng.
      Bạn có thể xoay, zoom trên từng chi tiết.
    </p>
    <a href=\"/compare\" class=\"btn btn-primary mb-4\">Compare Parts</a>
    
    <!-- 
      Chúng ta tạo lưới hiển thị bằng Bootstrap:
      row-cols-1 row-cols-md-3 nghĩa là: 
      - trên màn hình nhỏ: mỗi hàng chỉ 1 cột
      - trên màn hình >= md: mỗi hàng 3 cột
    -->
    <div class=\"row row-cols-1 row-cols-md-3 g-4\">
      {% for part_id, stl_path in parts_list %}
      <div class=\"col\">
        <div class=\"card\">
          <div class=\"model-container\" id=\"model-container-{{ loop.index }}\">
            <div class=\"model-title\">{{ part_id }}</div>
          </div>
        </div>
      </div>
      {% endfor %}
    </div>
  </div>

  <script>
    // Danh sách đường dẫn STL truyền từ Flask sang qua render_template_string
    const stlPaths = [
      {% for part_id, stl_path in parts_list %}
        "{{ stl_path }}"{% if not loop.last %},{% endif %}
      {% endfor %}
    ];

    // Khởi tạo từng viewer
    stlPaths.forEach((stlPath, index) => {
      initThreeJSViewer(index + 1, stlPath);
    });

    function initThreeJSViewer(index, stlPath) {
      const container = document.getElementById(`model-container-${index}`);

      // Scene, camera
      const scene = new THREE.Scene();
      scene.background = new THREE.Color("#f0f0f0");

      const camera = new THREE.PerspectiveCamera(
        45,
        container.clientWidth / container.clientHeight,
        0.1,
        1000
      );
      camera.position.set(0, 0, 70);

      // Renderer
      const renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setSize(container.clientWidth, container.clientHeight);
      container.appendChild(renderer.domElement);

      // OrbitControls
      const controls = new THREE.OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.05;
      controls.rotateSpeed = 0.5;
      controls.zoomSpeed = 1.0;

      // Ánh sáng
      const hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 1);
      hemiLight.position.set(0, 200, 0);
      scene.add(hemiLight);

      const dirLight = new THREE.DirectionalLight(0xffffff, 0.5);
      dirLight.position.set(0, 50, 50);
      scene.add(dirLight);

      // Tải STL
      const loader = new THREE.STLLoader();
      loader.load(stlPath, function (geometry) {
        // Đưa trọng tâm về gốc
        geometry.center();

        // Tính bounding box để xác định kích thước
        let tempMesh = new THREE.Mesh(geometry);
        const box = new THREE.Box3().setFromObject(tempMesh);
        const sizeVec = box.getSize(new THREE.Vector3());
        const largestDim = Math.max(sizeVec.x, sizeVec.y, sizeVec.z);

        // Scale up so it looks bigger in the container
        // Increase scaleFactor to enlarge model further
        const scaleFactor = 120 / largestDim;
        geometry.applyMatrix4(new THREE.Matrix4().makeScale(scaleFactor, scaleFactor, scaleFactor));

        // Recompute bounding box after scaling
        geometry.computeBoundingBox();
        geometry.center();

        // Now create material & mesh
        const material = new THREE.MeshPhongMaterial({ color: 0x5588aa });
        const mesh = new THREE.Mesh(geometry, material);
        scene.add(mesh);

        // Tính bounding box để canh camera (after scaling)
        const finalBox = new THREE.Box3().setFromObject(mesh);
        const size = finalBox.getSize(new THREE.Vector3()).length();
        const center = finalBox.getCenter(new THREE.Vector3());

        // Thiết lập camera
        const fitOffset = 1.02; // smaller offset to fill even more space
        const fitHeightDistance =
          fitOffset * Math.max(size, size / (2 * Math.atan((Math.PI * camera.fov) / 360)));
        const direction = new THREE.Vector3()
          .subVectors(camera.position, center)
          .normalize()
          .multiplyScalar(fitHeightDistance);

        camera.position.copy(center).add(direction);
        camera.lookAt(center);

        // OrbitControls xoay quanh trung tâm vật
        controls.target.copy(center);
        controls.update();
      });

      // Vòng lặp render
      function animate() {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
      }
      animate();

      // Xử lý khi thay đổi kích thước cửa sổ
      window.addEventListener("resize", () => {
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
      });
    }
  </script>

  <!-- Bootstrap JS (nếu cần) -->
  <script src=\"https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/js/bootstrap.bundle.min.js\"></script>
</body>
</html>
"""

# ----------------------------
# HTML cho trang so sánh (Compare)
# ----------------------------
HTML_3D_COMPARE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Compare Page</title>
  <!-- Bootstrap -->
  <link
    href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css"
    rel="stylesheet"
  />
  <!-- Three.js -->
  <script src="https://cdn.jsdelivr.net/npm/three@0.131.3/build/three.min.js"></script>
  <!-- STL Loader -->
  <script src="https://cdn.jsdelivr.net/npm/three@0.131.3/examples/js/loaders/STLLoader.js"></script>
  <!-- OrbitControls -->
  <script src="https://cdn.jsdelivr.net/npm/three@0.131.3/examples/js/controls/OrbitControls.js"></script>
  <style>
    .model-container {
      width: 100%;
      height: 400px;
      border: 1px solid #ccc;
      position: relative;
    }
    .model-title {
      position: absolute;
      top: 5px; 
      left: 5px;
      background-color: rgba(255,255,255,0.8);
      padding: 4px 8px;
      border-radius: 4px;
    }
  </style>
</head>
<body class="bg-light">

<div class="container py-4">
  <h1 class="mb-4">Compare Page</h1>
  <p>
    Compare first part with the rest.<br>
  </p>

  <!-- row-cols-md-2: trên màn hình md trở lên, mỗi hàng 2 cột -->
  <div class="row row-cols-1 row-cols-md-2 g-4">
    {% for stls in compare_list %}
    <div class="col">
      <div class="model-container" id="compare-container-{{ loop.index }}">
        <!-- Label đúng màu tương ứng STL -->
        <div class="model-title">
          <span style="color: #ff0000;">{{ stls[0][0] }}</span> -
          <span style="color: #0000ff;">{{ stls[1][0] }}</span>
        </div>
      </div>
    </div>
    {% endfor %}
  </div>
</div>

<script>
  // pairs = [
  //   [ "stl_path_ref", "stl_path_other" ],
  //   [ "stl_path_ref", "stl_path_other" ],
  //   ...
  // ]
  const pairs = [
    {% for stls in compare_list %}
      ["{{ stls[0][1] }}","{{ stls[1][1] }}"]{% if not loop.last %},{% endif %}
    {% endfor %}
  ];

  // Tạo viewer cho từng cặp
  pairs.forEach((paths, idx) => {
    initOverlayViewer(paths, idx+1);
  });

  function initOverlayViewer(paths, containerIndex) {
    // Mỗi ô => overlay 2 STL
    const container = document.getElementById(`compare-container-${containerIndex}`);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#f0f0f0");

    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.1,
      1000
    );
    camera.position.set(0,0,100);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;

    // Ánh sáng
    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x444444, 1);
    scene.add(hemiLight);

    let loadedCount = 0;
    function onLoadGeometry(geometry, color) {
      geometry.center();
      const tempMesh = new THREE.Mesh(geometry);
      const box = new THREE.Box3().setFromObject(tempMesh);
      const sizeVec = box.getSize(new THREE.Vector3());
      const largestDim = Math.max(sizeVec.x, sizeVec.y, sizeVec.z);

      const scaleFactor = 120 / largestDim;
      geometry.applyMatrix4(
        new THREE.Matrix4().makeScale(scaleFactor, scaleFactor, scaleFactor)
      );
      geometry.center();

      const material = new THREE.MeshPhongMaterial({ 
        color: color, 
        transparent: true, 
        opacity: 0.6
      });
      const mesh = new THREE.Mesh(geometry, material);
      scene.add(mesh);

      loadedCount++;
      if (loadedCount === 2) fitCamera();
    }

    function fitCamera() {
      const box = new THREE.Box3().setFromObject(scene);
      const size = box.getSize(new THREE.Vector3()).length();
      const center = box.getCenter(new THREE.Vector3());

      const fitOffset = 1.1;
      const fitHeightDistance = fitOffset * Math.max(
        size,
        size / (2 * Math.atan((Math.PI * camera.fov) / 360))
      );
      const direction = new THREE.Vector3()
        .subVectors(camera.position, center)
        .normalize()
        .multiplyScalar(fitHeightDistance);

      camera.position.copy(center).add(direction);
      camera.lookAt(center);
      controls.target.copy(center);
      controls.update();
    }

    const loader = new THREE.STLLoader();
    // Part ref => màu đỏ
    loader.load(paths[0],
      geometry => onLoadGeometry(geometry, 0xff0000),
      undefined,
      err => console.error(err)
    );
    // Part so sánh => màu xanh
    loader.load(paths[1],
      geometry => onLoadGeometry(geometry, 0x0000ff),
      undefined,
      err => console.error(err)
    );

    function animate() {
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }
    animate();

    // Xử lý resize
    window.addEventListener("resize", () => {
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    });
  }
</script>

<!-- Bootstrap JS -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

HTML_3D_SINGLE = """
<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Professional 3D Viewer (STL/OBJ)</title>
    <style>
        body { margin: 0; overflow: hidden; }
        canvas { display: block; }
        .dg { position: absolute; z-index: 10; }
    </style>
</head>
<body>
<script src=\"https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js\"></script>
<script src=\"https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/STLLoader.js\"></script>
<script src=\"https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/OBJLoader.js\"></script>
<script src=\"https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js\"></script>
<script src=\"https://cdn.jsdelivr.net/npm/dat.gui\"></script>

<script>
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth/window.innerHeight, 0.1, 1000);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setClearColor(new THREE.Color('#f0f4fa'), 1);
    renderer.shadowMap.enabled = true;
    document.body.appendChild(renderer.domElement);

    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.1;

    scene.add(new THREE.AmbientLight(0xcccccc, 0.4));
    const keyLight = new THREE.DirectionalLight(0xffffff, 0.8);
    keyLight.position.set(-2, 4, 2);
    scene.add(keyLight);

    const gridSize = 200;
    scene.add(new THREE.GridHelper(gridSize, 50));
    scene.add(new THREE.AxesHelper(100));

    const material = new THREE.MeshPhysicalMaterial({
        color: 0x0077ff, metalness: 0.7, roughness: 0.3,
        clearcoat: 0.5, clearcoatRoughness: 0.1
    });

    const gui = new dat.GUI();
    const params = {
        color: material.color.getHex(),
        metalness: material.metalness,
        roughness: material.roughness
    };

    gui.addColor(params, 'color').onChange(value => material.color.set(value));
    gui.add(params, 'metalness', 0, 1).onChange(value => material.metalness = value);
    gui.add(params, 'roughness', 0, 1).onChange(value => material.roughness = value);

    const fileUrl = '{{ file_url }}';
    const fileType = fileUrl.split('.').pop().toLowerCase();

    function setupMesh(geometryOrObj) {
        let mesh;
        if (geometryOrObj.isGeometry || geometryOrObj.isBufferGeometry) {
            mesh = new THREE.Mesh(geometryOrObj, material);
        } else {
            mesh = geometryOrObj;
            mesh.traverse(child => { if (child instanceof THREE.Mesh) child.material = material; });
        }

        const bbox = new THREE.Box3().setFromObject(mesh);
        const size = bbox.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const scaleFactor = gridSize / maxDim;
        mesh.scale.setScalar(scaleFactor);

        bbox.setFromObject(mesh);
        bbox.getCenter(mesh.position).multiplyScalar(-1);

        scene.add(mesh);
        camera.position.set(gridSize, gridSize, gridSize);
        controls.update();
    }

    if (fileType === 'stl') {
        new THREE.STLLoader().load(fileUrl, setupMesh);
    } else if (fileType === 'obj') {
        new THREE.OBJLoader().load(fileUrl, setupMesh);
    }

    function animate() {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
    }

    animate();

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    }, false);
</script>
</body>
</html>
"""
