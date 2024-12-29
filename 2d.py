import plotly.graph_objects as go
import pandas as pd
import numpy as np
from PIL import Image

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
            'football': '#654321'  # Changed football color to brown
        }
                
    def create_animation_controls(self):
        sliders_dict = {
            "active": 0,
            "yanchor": "top",
            "xanchor": "left",
            "currentvalue": {
                "font": {"size": 16},
                "prefix": "Frame:",
                "visible": True,
                "xanchor": "right",
                "offset": 0
            },
            "transition": {"duration": 300, "easing": "cubic-in-out"},
            "pad": {"b": 0, "t": 0},  # Remove all padding
            "len": 1.0,  # Full width
            "x": 0,  # Start at far left
            "y": 0,
            "tickwidth": 0,  # Remove tick width
            "tickcolor": "rgba(0,0,0,0)",  # Transparent instead of empty string
            "ticklen": 0,  # Remove tick length
            "minorticklen": 0,  # Remove minor tick length
            "steps": []
        }

        return None, sliders_dict


    def create_field_markers(self):
        """Create the football field with endzones and yard lines using 2D shapes"""
        field_elements = []
        
        # Create main field (green)
        field_elements.append(
            go.Scatter(
                x=[0, 120, 120, 0, 0],
                y=[0, 0, 53.3, 53.3, 0],
                fill="toself",
                fillcolor='rgba(0, 153, 0, 0.4)',  # Lighter green for better visibility
                line=dict(width=0),
                showlegend=False,
                hoverinfo='none'
            )
        )
        
        # Create endzones
        # Left endzone
        field_elements.append(
            go.Scatter(
                x=[0, 10, 10, 0, 0],
                y=[0, 0, 53.3, 53.3, 0],
                fill="toself",
                fillcolor='rgba(0, 0, 153, 0.4)',  # Lighter blue
                line=dict(width=0),
                showlegend=False,
                hoverinfo='none'
            )
        )
        
        # Right endzone
        field_elements.append(
            go.Scatter(
                x=[110, 120, 120, 110, 110],
                y=[0, 0, 53.3, 53.3, 0],
                fill="toself",
                fillcolor='rgba(153, 0, 0, 0.4)',  # Lighter red
                line=dict(width=0),
                showlegend=False,
                hoverinfo='none'
            )
        )
        
        # Add yard lines
        for yard in range(10, 111, 5):
            field_elements.append(
                go.Scatter(
                    x=[yard, yard],
                    y=[0, 53.3],
                    mode='lines',
                    line=dict(color='rgba(255, 255, 255, 0.30)', width=2),
                    showlegend=False,
                    hoverinfo='none'
                )
            )
        
        # Add hash marks
        # Lower hash marks
        for yard in range(10, 111):
            field_elements.append(
                go.Scatter(
                    x=[yard, yard],
                    y=[22.5, 23.5],
                    mode='lines',
                    line=dict(color='rgba(255, 255, 255, 0.25)', width=0.75),
                    showlegend=False,
                    hoverinfo='none'
                )
            )
        
        # Upper hash marks
        for yard in range(10, 111):
            field_elements.append(
                go.Scatter(
                    x=[yard, yard],
                    y=[29.8, 30.8],
                    mode='lines',
                    line=dict(color='rgba(255, 255, 255, 0.25)', width=0.75),
                    showlegend=False,
                    hoverinfo='none'
                )
            )
        
        # Add sidelines and endlines
        field_elements.append(
            go.Scatter(
                x=[0, 120, 120, 0, 0],
                y=[0, 0, 53.3, 53.3, 0],
                mode='lines',
                line=dict(color='rgba(255, 255, 255, 0.5)', width=1.5),
                showlegend=False,
                hoverinfo='none'
            )
        )
        
        return field_elements
    def animate_play(self, tracking_df, play_df):
        """
        Create an animated visualization of an NFL play with field background.
        """
        gameId = tracking_df.gameId.iloc[0]
        playId = tracking_df.playId.iloc[0]

        # Get play information
        play_info = play_df.iloc[0]
        line_of_scrimmage = play_info.absoluteYardlineNumber
        first_down_marker = line_of_scrimmage + play_info.yardsToGo
        down = play_info.down
        quarter = play_info.quarter
        gameClock = play_info.gameClock
        playDescription = play_info.playDescription

        # Split long play descriptions
        if len(playDescription.split()) > 15 and len(playDescription) > 115:
            playDescription = " ".join(playDescription.split()[:16]) + \
                "<br>" + " ".join(playDescription.split()[16:])

        updatemenus_dict, sliders_dict = self.create_animation_controls()
        frames = []
        
        # Get field elements once - they'll be the same for all frames
        field_elements = self.create_field_markers()
        
        # Create frames for each tracking moment
        for frameId in sorted(tracking_df.frameId.unique()):
            # Start with field elements for each frame
            data = field_elements.copy()
            
            # Add line of scrimmage and first down lines
            for line_x, color in [(line_of_scrimmage, 'rgba(135, 206, 235, 0.4)'),  # Light blue for LOS
                                (first_down_marker, 'rgba(255, 255, 0, 0.8)')]:
                data.append(
                    go.Scatter(
                        x=[line_x, line_x],
                        y=[0, 53.3],
                        line_dash='dash',
                        line_color=color,
                        line_width=2,
                        showlegend=False,
                        hoverinfo='none'
                    )
                )

            # Plot players
            frame_data = tracking_df[tracking_df.frameId == frameId]
        
            # Handle players
            for club in frame_data.club.unique():
                if pd.isna(club):
                    continue
                    
                club_data = frame_data[(frame_data.club == club) & (frame_data.displayName != 'football')]  # Added condition to exclude football
                hover_text = []
                for _, player in club_data.iterrows():
                    if pd.isna(player.displayName):
                        continue
                    hover_text.append(
                        f"Name: {player.displayName}<br>"
                        f"Jersey: {player.jerseyNumber}<br>"
                        f"Speed: {player.s:.1f} mph<br>"
                        f"Direction: {player.dir:.1f}°"
                    )
                
                data.append(
                    go.Scatter(
                        x=club_data["x"],
                        y=club_data["y"],
                        mode='markers',
                        marker=dict(
                            color=self.colors.get(club, "#000000"),
                            size=12,
                            line=dict(color='white', width=0.5)
                        ),
                        name=club,
                        hovertext=hover_text,
                        hoverinfo="text"
                    )
                )
                # Handle football separately
            football_data = frame_data[frame_data.nflId.isna()]
            if not football_data.empty:
                data.append(
                    go.Scatter(
                        x=football_data["x"],
                        y=football_data["y"],
                        mode='markers',
                        marker=dict(
                            color=self.colors['football'],
                            size=8,
                            symbol='diamond',
                            line=dict(color='white', width=0.5)
                        ),
                        name='football',
                        hoverinfo='none'
                    )
                )
            
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
            
            frames.append(go.Frame(data=data, name=str(frameId)))

        # Set up the layout (rest of the code remains the same)
        layout = go.Layout(
            autosize=False,
            width=900,
            height=450,
            margin=dict(l=0, r=0, t=50, b=0),
            xaxis=dict(
                range=[0, 120],
                autorange=False,
                showgrid=False,
                showticklabels=False,
                zeroline=False,
                fixedrange=True
            ),
            yaxis=dict(
                range=[0, 53.3],
                autorange=False,
                showgrid=False,
                showticklabels=False,
                zeroline=False,
                scaleanchor="x",
                scaleratio=1,
                fixedrange=True
            ),
            plot_bgcolor='black',  # Changed to black for better contrast
            paper_bgcolor='white',
            title=dict(
                text=f"GameId: {gameId}, PlayId: {playId} | {gameClock} {quarter}Q<br>{playDescription}",
                font=dict(size=14, color='black'),
                y=0.98,
                x=0.5,
                xanchor='center',
                yanchor='top'
            ),
            sliders=[sliders_dict],
            showlegend=False,
            dragmode=False
        )

        # Create figure with field elements in initial data
        fig = go.Figure(
            data=frames[0]["data"],  # This now includes field elements
            layout=layout,
            frames=frames[1:]
        )

        # Add down markers with improved visibility
        for y_val in [0, 53]:
            fig.add_annotation(
                x=first_down_marker,
                y=y_val,
                text=str(down),
                showarrow=False,
                font=dict(
                    family="Courier New, monospace",
                    size=16,
                    color="black"
                ),
                align="center",
                bordercolor="black",
                borderwidth=2,
                borderpad=4,
                bgcolor="rgba(255, 127, 14, 1)",
                opacity=1
            )

        return fig