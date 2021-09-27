from talon import skia, ui, Module, cron, actions, clip
from user.talon_hud.layout_widget import LayoutWidget
from user.talon_hud.widget_preferences import HeadUpDisplayUserWidgetPreferences
from user.talon_hud.utils import layout_rich_text, remove_tokens_from_rich_text, linear_gradient, hit_test_icon
from user.talon_hud.content.typing import HudRichTextLine, HudPanelContent, HudButton, HudIcon
from talon.types.point import Point2d

icon_radius = 10

class HeadUpWalkThroughPanel(LayoutWidget):
    preferences = HeadUpDisplayUserWidgetPreferences(type="walk_through", x=910, y=1000, width=100, height=20, limit_x=480, limit_y=700, limit_width=960, limit_height=124, enabled=False, sleep_enabled=True, alignment="center", expand_direction="up", font_size=24)
    mouse_enabled = True

    # Top, right, bottom, left, same order as CSS padding
    padding = [10, 20, 10, 8]
    line_padding = 6
    
    # Options given to the context menu
    buttons = [
        HudButton("next_icon", "Skip this step", ui.Rect(0,0,0,0), lambda widget: actions.user.hud_skip_walkthrough_step()),
        HudButton("check_icon", "Mark as done", ui.Rect(0,0,0,0), lambda widget: actions.user.hud_skip_walkthrough_all())
    ]

    subscribed_content = ["mode"]
    content = {
        'mode': 'command',
    }
    panel_content = HudPanelContent('walk_through', '', [''], [], 0, False)
    animation_max_duration = 30

    def update_panel(self, panel_content) -> bool:
        return super().update_panel(panel_content)
    
    def on_mouse(self, event):
        if event.button == 1 and event.event == "mouseup":            
            actions.user.show_context_menu(self.id, event.gpos.x, event.gpos.y, self.buttons)
        elif event.button == 0 and event.event == "mouseup":
            actions.user.hide_context_menu()
        super().on_mouse(event)

    def set_preference(self, preference, value, persisted=False):
        self.mark_layout_invalid = True
        super().set_preference(preference, value, persisted)
        
    def load_theme_values(self):
        self.intro_animation_start_colour = self.theme.get_colour_as_ints('intro_animation_start_colour')
        self.intro_animation_end_colour = self.theme.get_colour_as_ints('intro_animation_end_colour')
        self.blink_difference = [
            self.intro_animation_end_colour[0] - self.intro_animation_start_colour[0],
            self.intro_animation_end_colour[1] - self.intro_animation_start_colour[1],
            self.intro_animation_end_colour[2] - self.intro_animation_start_colour[2]        
        ]

    def layout_content(self, canvas, paint):
        paint.textsize = self.font_size
        self.line_padding = int(self.font_size / 2) + 1 if self.font_size <= 17 else 5
        
        horizontal_alignment = "right" if self.limit_x < self.x else "left"
        vertical_alignment = "bottom" if self.limit_y < self.y else "top"
        
        if self.alignment == "center" or \
            ( self.x + self.width < self.limit_x + self.limit_width and self.limit_x < self.x ):
            horizontal_alignment = "center"
    
        layout_width = max(self.width - self.padding[1] * 2 - self.padding[3] * 2, 
            self.limit_width - self.padding[1] * 2 - self.padding[3] * 2)
    
        content_text = [] if self.minimized else layout_rich_text(paint, self.panel_content.content[0], layout_width, self.limit_height)
        layout_pages = []
        
        line_count = 0
        total_text_width = 0
        total_text_height = 0
        current_line_length = 0        
        page_height_limit = self.limit_height
        
        # We do not render content if the text box is minimized
        current_content_height = 0
        current_page_text = []
        current_line_height = 0
        if not self.minimized:
            line_count = 0
            for index, text in enumerate(content_text):
                line_count = line_count + 1 if text.x == 0 else line_count
                current_line_length = current_line_length + text.width if text.x != 0 else text.width
                total_text_width = max( total_text_width, current_line_length )
                total_text_height = total_text_height + text.height + self.line_padding if text.x == 0 else total_text_height
                
                current_content_height = total_text_height + self.padding[0] + self.padding[2]
                current_line_height = text.height + self.line_padding
                if page_height_limit > current_content_height:
                    current_page_text.append(text)
                    
                # We have exceeded the page height limit, append the layout and try again
                else:
                    width = min( self.limit_width, max(self.width, total_text_width + self.padding[1] + self.padding[3]))
                    height = self.limit_height
                    x = self.x if horizontal_alignment == "left" else self.limit_x + self.limit_width - width
                    if horizontal_alignment == "center":
                        x = self.limit_x + ( self.limit_width - width ) / 2
                    y = self.limit_y if vertical_alignment == "top" else self.limit_y + self.limit_height - height
                    layout_pages.append({
                        "rect": ui.Rect(x, y, width, height), 
                        "line_count": max(1, line_count - 1),
                        "content_text": current_page_text,
                        "content_height": current_content_height
                    })
                    
                    # Reset the variables
                    total_text_height = current_line_height
                    current_page_text = [text]
                    line_count = 1
                  
        # Make sure the remainder of the content gets placed on the final page
        if len(current_page_text) > 0 or len(layout_pages) == 0:
            
            # If we are dealing with a single line going over to the only other page
            # Just remove the footer to make up for space
            if len(layout_pages) == 1 and line_count == 1:
                layout_pages[0]['line_count'] = layout_pages[0]['line_count'] + 1
                layout_pages[0]['content_text'].extend(current_page_text)
                layout_pages[0]['content_height'] += current_line_height
            else: 
                width = min( self.limit_width, max(self.width, total_text_width + self.padding[1] + self.padding[3]))
                content_height = total_text_height + self.padding[0] + self.padding[2]
                height = min(self.limit_height, max(self.height, content_height))
                x = self.x if horizontal_alignment == "left" else self.limit_x + self.limit_width - width
                if horizontal_alignment == "center":
                    x = self.limit_x + ( self.limit_width - width ) / 2                
                y = self.limit_y if vertical_alignment == "top" else self.limit_y + self.limit_height - height
                
                layout_pages.append({
                    "rect": ui.Rect(x, y, width, height), 
                    "line_count": max(1, line_count + 2 ),
                    "content_text": current_page_text,
                    "content_height": content_height
                })
                
        return layout_pages
    
    def draw_content(self, canvas, paint, dimensions) -> bool:
        # Disable if there is no content
        if len(self.panel_content.content[0]) == 0:
            self.disable(True)
            return False

        paint.textsize = self.font_size
        
        paint.style = paint.Style.FILL
        
        # Draw the background first
        background_colour = self.theme.get_colour('text_box_background', 'F5F5F5')
        paint.color = background_colour
        self.draw_background(canvas, paint, dimensions["rect"])
        
        paint.color = self.theme.get_colour('text_colour')
        self.draw_content_text(canvas, paint, dimensions)
        
        return False

    def draw_animation(self, canvas, animation_tick):
        if self.enabled and len(self.panel_content.content[0]) > 0:
            paint = canvas.paint
            if self.mark_layout_invalid and animation_tick == self.animation_max_duration - 1:
                self.layout = self.layout_content(canvas, paint)
                if self.page_index > len(self.layout) - 1:
                    self.page_index = len(self.layout) -1
            
            dimensions = self.layout[self.page_index]['rect']
            
            # Determine colour of the animation
            animation_progress = ( animation_tick - self.animation_max_duration ) / self.animation_max_duration
            red = self.intro_animation_start_colour[0] - int( self.blink_difference[0] * animation_progress )
            green = self.intro_animation_start_colour[1] - int( self.blink_difference[1] * animation_progress )
            blue = self.intro_animation_start_colour[2] - int( self.blink_difference[2] * animation_progress )
            red_hex = '0' + format(red, 'x') if red <= 15 else format(red, 'x')
            green_hex = '0' + format(green, 'x') if green <= 15 else format(green, 'x')
            blue_hex = '0' + format(blue, 'x') if blue <= 15 else format(blue, 'x')
            paint.color = red_hex + green_hex + blue_hex
            
            
            horizontal_alignment = "right" if self.limit_x < self.x else "left"
            if self.alignment == "center" or \
                ( self.x + self.width < self.limit_x + self.limit_width and self.limit_x < self.x ):
                horizontal_alignment = "center"
            
            growth = (self.animation_max_duration - animation_tick ) / self.animation_max_duration
            easeInOutQuint = 16 * growth ** 5 if growth < 0.5 else 1 - pow(-2 * growth + 2, 5) / 2
            
            width = dimensions.width * easeInOutQuint            
            if horizontal_alignment == "left":
                x = dimensions.x
            elif horizontal_alignment == "right":
                x = self.limit_x + self.limit_width - width
            elif horizontal_alignment == "center":
                x = self.limit_x + ( self.limit_width / 2 ) - ( width / 2 )
            
            rect = ui.Rect(x, dimensions.y, width, dimensions.height)
            self.draw_background(canvas, paint, rect)
            
            if animation_tick == 1:
                return self.draw(canvas)
            return True
        else:
            return False

    def draw_content_text(self, canvas, paint, dimensions) -> int:
        """Draws the content and returns the height of the drawn content"""
        paint.textsize = self.font_size
        
        rich_text = dimensions["content_text"]
        content_height = dimensions["content_height"]
        line_count = dimensions["line_count"]
        dimensions = dimensions["rect"]
       
        text_x = dimensions.x + self.padding[3]
        text_y = dimensions.y + self.padding[0] + self.padding[2]
        
        line_height = ( content_height - self.padding[0] - self.padding[2] ) / line_count
        self.draw_rich_text(canvas, paint, rich_text, text_x, text_y, line_height)

    def draw_background(self, canvas, paint, rect):
        radius = 10
        rrect = skia.RoundRect.from_rect(rect, x=radius, y=radius)
        canvas.draw_rrect(rrect)