import plotly.graph_objects as go
import streamlit as st
import pymeshlab
import io
import trimesh
import chardet
import os
from tempfile import NamedTemporaryFile


def load_meshset(filename):
    ms = pymeshlab.MeshSet()
    ms.load_new_mesh(filename)
    return ms


def get_vertices_and_faces_from_meshset(ms):
    m = ms.current_mesh()
    vertices = m.vertex_matrix()
    faces = m.face_matrix()
    return vertices, faces


def load_meshset_from_bytes(file_bytes: bytes, file_extension: str = "jt"):
    """
    Load mesh từ bytes cho các định dạng chưa thể đọc thẳng từ memory (vd: .jt).
    Tạo file tạm, ghi bytes, sau đó dùng pymeshlab load.
    """
    ms = pymeshlab.MeshSet()

    # Ghi vào file tạm, xoá ngay khi ra khỏi 'with'
    with NamedTemporaryFile(suffix=f".{file_extension}") as tmp:
        tmp.write(file_bytes)
        tmp.flush()  # đảm bảo dữ liệu đã ghi
        ms.load_new_mesh(tmp.name)
    return ms

class Display3D:
    def __init__(self):
        self.config = {"displayModeBar": False}

    def setup_figure(self):
        self.fig = go.Figure()  # Khởi tạo lại fig mỗi lần setup
        self.fig.update_layout(
            autosize=True,  # Let it auto-adjust to the best fit
            margin=dict(l=0, r=0, b=0, t=0),
            scene=dict(
                xaxis=dict(showbackground=False, visible=False),  # Hide the x-axis
                yaxis=dict(showbackground=False, visible=False),  # Hide the y-axis
                zaxis=dict(showbackground=False, visible=False),  # Hide the z-axis
            ),
            paper_bgcolor="rgba(0,0,0,0)",  # Transparent background
            plot_bgcolor="rgba(0,0,0,0)",  # Transparent background
            showlegend=False,
        )

    def display_pcloud(self, *clouds, color="Gray"):
        self.setup_figure()  # Khởi tạo lại fig mỗi lần gọi display_pcloud
        # Iterate over each cloud passed as an argument
        for i, cloud in enumerate(clouds):
            # Convert tensors to numpy arrays for plotting
            if hasattr(cloud, "detach"):  # Check if the cloud variable is a tensor
                cloud_np = (
                    cloud.detach().cpu().numpy()
                    if cloud.requires_grad
                    else cloud.cpu().numpy()
                )
            else:
                cloud_np = cloud  # If it's already a numpy array

            # Add a scatter3d trace for each cloud
            self.fig.add_trace(
                go.Scatter3d(
                    x=cloud_np[:, 0],
                    y=cloud_np[:, 1],
                    z=cloud_np[:, 2],
                    mode="markers",
                    marker=dict(size=2),
                )
            )

        # Display the figure using Streamlit, with the config adjustments
        st.plotly_chart(self.fig, use_container_width=True, config=self.config)

    def display_mesh(self, files):
        self.setup_figure()  # Khởi tạo lại fig mỗi lần gọi display_mesh
        colors = ["gray", "red", "green", "yellow", "blue", "magenta", "cyan"]

        for index, file in enumerate(files):
            ms = load_meshset(file)
            vertices, faces = get_vertices_and_faces_from_meshset(ms)
            x, y, z = vertices.T
            i, j, k = faces.T
            self.fig.add_trace(
                go.Mesh3d(
                    x=x,
                    y=y,
                    z=z,
                    i=i,
                    j=j,
                    k=k,
                    color=colors[index % len(colors)],
                    # opacity=0.5
                )
            )

        # Display the figure using Streamlit, with the config adjustments
        st.plotly_chart(self.fig, use_container_width=True, config=self.config)

    def display_3d(self, files):
        fig = go.Figure()
        colors = ["gray", "red", "green", "yellow", "blue", "magenta", "cyan"]

        for index, file in enumerate(files):
            ms = load_meshset(file)
            vertices, faces = get_vertices_and_faces_from_meshset(ms)
            x, y, z = vertices.T
            i, j, k = faces.T
            fig.add_trace(
                go.Mesh3d(
                    x=x,
                    y=y,
                    z=z,
                    i=i,
                    j=j,
                    k=k,
                    color=colors[index % len(colors)],
                    # opacity=0.5
                )
            )

        fig.update_layout(
            autosize=True,  # Let it auto-adjust to the best fit
            margin=dict(l=0, r=0, b=0, t=0),
            # width=100,
            # height=100,
            scene=dict(
                xaxis=dict(showbackground=False, visible=False),  # Hide the x-axis
                yaxis=dict(showbackground=False, visible=False),  # Hide the y-axis
                zaxis=dict(showbackground=False, visible=False),
            ),
            paper_bgcolor="rgba(0,0,0,0)",  # Transparent background
            plot_bgcolor="rgba(0,0,0,0)",  # Transparent background
            showlegend=False,
        )
        config = {"displayModeBar": False}  # This will hide the toolbar

        st.plotly_chart(fig, use_container_width=True, config=config)

    def display_mesh_from_bytes(self, files_bytes, file_type='jt'):
        """
        Hiển thị nhiều mesh được load trực tiếp từ object bytes (đặc biệt với .jt).
        """
        self.setup_figure()
        colors = ["gray", "red", "green", "yellow", "blue", "magenta", "cyan"]

        for index, file_bytes in enumerate(files_bytes):
            # Với file_type='jt' (hoặc format binary khác), ta phải load qua NamedTemporaryFile
            ms = load_meshset_from_bytes(file_bytes, file_extension=file_type)

            vertices, faces = get_vertices_and_faces_from_meshset(ms)
            x, y, z = vertices.T
            i, j, k = faces.T
            self.fig.add_trace(
                go.Mesh3d(
                    x=x,
                    y=y,
                    z=z,
                    i=i,
                    j=j,
                    k=k,
                    color=colors[index % len(colors)],
                )
            )

        st.plotly_chart(self.fig, use_container_width=True, config=self.config)