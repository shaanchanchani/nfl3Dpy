import plotly.graph_objects as go
import pandas as pd
import numpy as np
from PIL import Image
from typing import Union, Tuple, Dict, List

class NFLPlayAnimator:
    def __init__(self):
        self.colors = {
            'ARI': "#97233F", 'ATL': "#A71930", 'BAL': '#241773', 'BUF': "#00338D",
            'CAR': "#0085CA", 'CHI': "#C83803", 'CIN': "#FB4F14", 'CLE': "#311D00",
            'DAL': '#003594', 'DEN': "#FB4F14", 'DET': "#0076B6", 'GB': "#203731",
            'HOU': "#03202F", 'IND': "#002C5F", 'JAX': "#9F792C", 'KC': "#E31837",
            'LA': "#003594", 'LAC': "#0080C6", 'LV': "#000000", 'MIA': "#008E97",
            'MIN': "#4F2683", 'NE': "#002244", 'NO': "#D3BC8D", 'NYG': "#0B2265",
            'NYJ': "#125740", 'PHI': "#004C54", 'PIT': "#FFB612", 'SEA': "#69BE28",
            'SF': "#AA0000", 'TB': '#D50A0A', 'TEN': "#4B92DB", 'WAS': "#5A1414",
            'football': '#654321'
        }
        self.GRAVITY = 10.725  # yards per second per second

    def add_z_coordinates(self, tracking_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """Add Z-coordinates to tracking data for pass visualization"""
        # Create a copy of the input DataFrame
        df = tracking_df.copy()
        
        # Get football-only data
        football_data = df[df['displayName'] == 'football'].copy()
        player_data = df[df['displayName'] != 'football'].copy()
        
        # Find pass_forward frame
        pass_forward_frame = football_data[football_data['event'] == 'pass_forward']['frameId'].min()
        
        # Find pass_arrived frame (look for any pass outcome event)
        arrival_events = ['pass_arrived', 'pass_outcome_interception', 
                         'pass_outcome_touchdown', 'pass_outcome_caught', 
                         'pass_outcome_incomplete']
        pass_arrived_frame = football_data[football_data['event'].isin(arrival_events)]['frameId'].min()
        
        if pd.isna(pass_forward_frame) or pd.isna(pass_arrived_frame):
            # If we can't find the exact frames, estimate them
            all_frames = sorted(football_data['frameId'].unique())
            snap_frame = football_data[football_data['event'] == 'ball_snap']['frameId'].min()
            
            if pd.isna(snap_frame):
                snap_frame = all_frames[0]
            
            # Estimate pass_forward as 1 second after snap
            pass_forward_frame = snap_frame + 10  # assuming 10 frames per second
            
            # Estimate pass_arrived as 2 seconds after pass_forward
            pass_arrived_frame = pass_forward_frame + 20
            
            # Ensure frames exist in the data
            while pass_forward_frame not in all_frames and pass_forward_frame < all_frames[-1]:
                pass_forward_frame += 1
            while pass_arrived_frame not in all_frames and pass_arrived_frame < all_frames[-1]:
                pass_arrived_frame += 1
            
            if pass_forward_frame >= all_frames[-1] or pass_arrived_frame >= all_frames[-1]:
                pass_forward_frame = all_frames[len(all_frames)//3]
                pass_arrived_frame = all_frames[2*len(all_frames)//3]
        
        # Calculate time since throw for all frames
        df['seconds_since_throw'] = (df['frameId'] - pass_forward_frame) / 10
        
        # Initialize z-coordinates
        df['z'] = 0
        df['z1'] = 0
        df['z2'] = 0
        
        # Get start and end positions
        start_pos = football_data[football_data['frameId'] == pass_forward_frame].iloc[0]
        end_pos = football_data[football_data['frameId'] == pass_arrived_frame].iloc[0]
        
        # Calculate distance and velocities
        distance = np.sqrt((start_pos['x'] - end_pos['x'])**2 + 
                         (start_pos['y'] - end_pos['y'])**2)
        
        time_of_flight = (pass_arrived_frame - pass_forward_frame) / 10
        vxy = distance / time_of_flight
        
        # Calculate vertical velocities
        vz = (time_of_flight * self.GRAVITY) / 2
        vz1 = (0.5 + 0.5 * self.GRAVITY * time_of_flight**2) / time_of_flight
        vz2 = (-0.5 + 0.5 * self.GRAVITY * time_of_flight**2) / time_of_flight
        
        # Calculate initial velocity and launch angle
        v_0 = np.sqrt(vz**2 + vxy**2)
        launch_angle = np.degrees(np.arctan(vz/vxy))
        
        # Calculate z-coordinates for the football
        football_mask = df['displayName'] == 'football'
        flight_mask = (df['frameId'] >= pass_forward_frame) & (df['frameId'] <= pass_arrived_frame)
        
        # Base height calculations
        df.loc[football_mask & flight_mask, 'z'] = (
            2 + vz * df.loc[football_mask & flight_mask, 'seconds_since_throw'] -
            0.5 * self.GRAVITY * df.loc[football_mask & flight_mask, 'seconds_since_throw']**2
        )
        
        df.loc[football_mask & flight_mask, 'z1'] = (
            1.5 + vz1 * df.loc[football_mask & flight_mask, 'seconds_since_throw'] -
            0.5 * self.GRAVITY * df.loc[football_mask & flight_mask, 'seconds_since_throw']**2
        )
        
        df.loc[football_mask & flight_mask, 'z2'] = (
            2.5 + vz2 * df.loc[football_mask & flight_mask, 'seconds_since_throw'] -
            0.5 * self.GRAVITY * df.loc[football_mask & flight_mask, 'seconds_since_throw']**2
        )
        
        # Create return dictionary with calculated metrics
        metrics = {
            'initial_velocity': v_0,
            'horizontal_velocity': vxy,
            'vertical_velocity': vz,
            'launch_angle': launch_angle,
            'time_of_flight': time_of_flight,
            'max_height': df['z'].max(),
            'distance': distance,
            'start_x': start_pos['x'],
            'start_y': start_pos['y'],
            'end_x': end_pos['x'],
            'end_y': end_pos['y'],
            'pass_forward_frame': pass_forward_frame,
            'pass_arrived_frame': pass_arrived_frame
        }
        
        return df, metrics
    
    def animate_play(self, tracking_df: pd.DataFrame, play_df: pd.DataFrame) -> go.Figure:
        """Create an animated 3D visualization of an NFL play"""
        # Add z-coordinates to tracking data
        tracking_df, play_metrics = self.add_z_coordinates(tracking_df)
        
        # Get play information
        play_info = play_df.iloc[0]
        gameId = tracking_df.gameId.iloc[0]
        playId = tracking_df.playId.iloc[0]
        
        # Create animation controls
        updatemenus_dict, sliders_dict = self.create_animation_controls()
        
        # Create base figure with field
        fig = go.Figure()
        
        # Add field surfaces
        field_surfaces = self.create_field_surface()
        for surface in field_surfaces:
            fig.add_trace(surface)
            
        # Create frames for animation
        frames = []
        for frameId in sorted(tracking_df.frameId.unique()):
            frame_data = tracking_df[tracking_df.frameId == frameId]
            
            # Create frame traces
            frame_traces = []
            
            # Add football
            football_data = frame_data[frame_data['displayName'] == 'football']
            if not football_data.empty:
                frame_traces.append(
                    go.Scatter3d(
                        x=football_data["x"],
                        y=football_data["y"],
                        z=football_data["z"],
                        mode='markers',
                        marker=dict(
                            color=self.colors['football'],
                            size=6,
                            symbol='diamond'
                        ),
                        name='football',
                        hoverinfo='none'
                    )
                )
            
            # Add players
            for team in frame_data.club.unique():
                if pd.isna(team):
                    continue
                    
                team_data = frame_data[(frame_data.club == team) & (frame_data.displayName != 'football')].copy()
                team_data['z'] = 1
                hover_text = [
                    f"Name: {player.displayName}<br>"
                    f"Jersey: {player.jerseyNumber}<br>"
                    f"Speed: {player.s:.1f} mph<br>"
                    f"Direction: {player.dir:.1f}°"
                    for _, player in team_data.iterrows() if not pd.isna(player.displayName)
                ]
                
                frame_traces.append(
                    go.Scatter3d(
                        x=team_data["x"],
                        y=team_data["y"],
                        z=team_data["z"],
                        mode='markers+text',
                        text=team_data["jerseyNumber"],
                        marker=dict(
                            color=self.colors.get(team, "#000000"),
                            size=12,
                            line=dict(color='white', width=1)
                        ),
                        name=team,
                        hovertext=hover_text,
                        hoverinfo="text",
                        textposition="middle center"
                    )
                )
            
            # Add frame to slider
            sliders_dict["steps"].append({
                "args": [
                    [frameId],
                    {"frame": {"duration": 100, "redraw": False},
                     "mode": "immediate",
                     "transition": {"duration": 0}}
                ],
                "label": str(frameId),
                "method": "animate"
            })
            
            # Create frame
            frames.append(go.Frame(
                data=frame_traces + field_surfaces,
                name=str(frameId)
            ))
        
        # Update layout with metrics
        title_text = (
            f"GameId: {gameId}, PlayId: {playId}<br>"
            f"{play_info.gameClock} {play_info.quarter}Q<br>"
            f"{play_info.playDescription}<br>"
            f"Launch Angle: {play_metrics['launch_angle']:.1f}°, "
            f"Initial Velocity: {play_metrics['initial_velocity']:.1f} yd/s, "
            f"Max Height: {play_metrics['max_height']:.1f} yd"
        )
        
        fig.update_layout(
            width=800,
            height=600,
            scene=dict(
                aspectmode='manual',
                aspectratio=dict(x=2.25, y=1, z=0.5),
                camera=dict(
                    up=dict(x=0, y=0, z=1),
                    # center=dict(x=0, y=0, z=0),
                    eye=dict(x=0.8, y=.8, z=0.7)  # Much closer eye position
                ),
                xaxis=dict(range=[0, 120], showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(range=[0, 53.3], showgrid=False, zeroline=False, showticklabels=False),
                zaxis=dict(range=[-1, 20], showgrid=False, zeroline=False, showticklabels=False)
            ),
            title=dict(
                text=title_text,
                font=dict(color='black')
            ),
            showlegend=False,
            updatemenus=updatemenus_dict,
            sliders=[sliders_dict]
        )
        
        # Add frames to figure
        fig.frames = frames

        return fig


    def create_animation_controls(self):
        """Create animation controls for the play visualization"""
        updatemenus_dict = [
            {
                "buttons": [
                    {
                        "args": [None, {"frame": {"duration": 100, "redraw": True},
                                    "fromcurrent": True,
                                    "transition": {"duration": 0}}],
                        "label": "Play",
                        "method": "animate"
                    },
                    {
                        "args": [[None], {"frame": {"duration": 0, "redraw": True},
                                        "mode": "immediate",
                                        "transition": {"duration": 0}}],
                        "label": "Pause",
                        "method": "animate"
                    }
                ],
                "direction": "left",
                "pad": {"r": 10, "t": 40},
                "showactive": False,
                "type": "buttons",
                "x": 0.1,
                "xanchor": "right",
                "y": 0,
                "yanchor": "top"
            }
        ]

        sliders_dict = {
            "active": 0,
            "yanchor": "top",
            "xanchor": "left",
            "currentvalue": {
                "font": {"size": 20},
                "prefix": "Frame: ",
                "visible": True,
                "xanchor": "right"
            },
            "transition": {"duration": 300, "easing": "cubic-in-out"},
            "pad": {"b": 5, "t": 15},
            "len": 0.9,
            "x": 0.1,
            "y": 0,
            "steps": []
        }

        return updatemenus_dict, sliders_dict
    
    def create_field_surface(self) -> List[go.Mesh3d]:
        """Create the football field surface with endzones and yard lines"""
        surfaces = []
        
        # Create main field (green)
        x, y, z = self._create_grid(10, 110, 0, 53.3, 0)
        surfaces.append(
            go.Mesh3d(
                x=x, y=y, z=z,
                color='green',
                showscale=False,
                hoverinfo='none'
            )
        )
        
        # Create endzones
        # Left endzone (blue)
        x, y, z = self._create_grid(0, 10, 0, 53.3, 0)
        surfaces.append(
            go.Mesh3d(
                x=x, y=y, z=z,
                color='blue',
                showscale=False,
                hoverinfo='none'
            )
        )
        
        # Right endzone (red)
        x, y, z = self._create_grid(110, 120, 0, 53.3, 0)
        surfaces.append(
            go.Mesh3d(
                x=x, y=y, z=z,
                color='red',
                showscale=False,
                hoverinfo='none'
            )
        )
        
        # Add yard lines
        for yard in range(10, 111, 5):
            x, y, z = self._create_grid(yard-0.1, yard+0.1, 0, 53.3, 0.1)
            surfaces.append(
                go.Mesh3d(
                    x=x, y=y, z=z,
                    color='white',
                    showscale=False,
                    hoverinfo='none'
                )
            )
        
        # Add hash marks
        # Lower hash marks
        for yard in range(10, 111):
            x, y, z = self._create_grid(yard-0.1, yard+0.1, 22.5, 23.5, 0.1)
            surfaces.append(
                go.Mesh3d(
                    x=x, y=y, z=z,
                    color='white',
                    showscale=False,
                    hoverinfo='none'
                )
            )
        
        # Upper hash marks
        for yard in range(10, 111):
            x, y, z = self._create_grid(yard-0.1, yard+0.1, 28.75, 29.75, 0.1)
            surfaces.append(
                go.Mesh3d(
                    x=x, y=y, z=z,
                    color='white',
                    showscale=False,
                    hoverinfo='none'
                )
            )
        
        return surfaces

    def _create_grid(self, x_min: float, x_max: float, y_min: float, y_max: float, z_val: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Helper function to create grid points for field surfaces"""
        x = np.array([x_min, x_min, x_max, x_max])
        y = np.array([y_min, y_max, y_max, y_min])
        z = np.full_like(x, z_val)
        
        return x, y, z