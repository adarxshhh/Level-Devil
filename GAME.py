import pygame
import sys
import math
import random
import struct

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Palette
COLOR_BG = (245, 238, 248)
COLOR_PLATFORM = (64, 52, 74)
COLOR_PLATFORM_ACCENT = (100, 85, 115)
COLOR_SPIKE = (220, 60, 90)
COLOR_DOOR = (255, 204, 77)
COLOR_DOOR_INNER = (240, 160, 40)
COLOR_TEXT = (50, 40, 60)

# Particle Color Palette (Cute Pastel Bursts)
PARTICLE_COLORS = [
    (255, 150, 180),  # Pastel Pink
    (255, 210, 230),  # Soft Rose
    (255, 240, 150),  # Lemon Chiffon
    (170, 220, 255),  # Sky Blue
    (255, 255, 255),  # Pure White
    (220, 180, 255),  # Lavender
]

# Physics
GRAVITY = 0.7
PLAYER_SPEED = 4.5
JUMP_FORCE = -12.5


# ==========================================
# PROCEDURAL 8-BIT SOUND GENERATOR
# ==========================================
class SoundFX:
    """Generates pure 8-bit style chiptune sounds in memory without external audio files."""
    def __init__(self):
        self.sample_rate = 22050
        try:
            pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=1, buffer=512)
            self.jump_sfx = self._synth_jump()
            self.death_sfx = self._synth_death()
            self.win_sfx = self._synth_win()
            self.troll_sfx = self._synth_troll()
            self.enabled = True
        except Exception:
            self.enabled = False

    def _build_sound(self, sample_generator, duration):
        total_samples = int(self.sample_rate * duration)
        buffer = bytearray()
        for i in range(total_samples):
            t = i / self.sample_rate
            sample_val = sample_generator(t, duration)
            sample_int = int(max(-1.0, min(1.0, sample_val)) * 32767)
            buffer += struct.pack('<h', sample_int)
        return pygame.mixer.Sound(buffer=bytes(buffer))

    def _synth_jump(self):
        # Cute rising chirp (Square wave + frequency sweep)
        def gen(t, dur):
            freq = 420 + (t / dur) * 580  # 420Hz -> 1000Hz
            phase = (t * freq) % 1.0
            val = 0.3 if phase < 0.5 else -0.3
            envelope = 1.0 - (t / dur)
            return val * envelope
        return self._build_sound(gen, 0.12)

    def _synth_death(self):
        # Descending sad bloop with warble
        def gen(t, dur):
            freq = max(60, 600 - (t / dur) * 480 + math.sin(t * 70) * 40)
            phase = (t * freq) % 1.0
            val = 0.35 if phase < 0.5 else -0.35
            envelope = math.exp(-3.5 * (t / dur))
            return val * envelope
        return self._build_sound(gen, 0.35)

    def _synth_win(self):
        # Arpeggio fanfare chime (C5 -> E5 -> G5 -> C6)
        notes = [523.25, 659.25, 783.99, 1046.50]
        def gen(t, dur):
            idx = min(len(notes) - 1, int((t / dur) * len(notes)))
            freq = notes[idx]
            # Triangle/soft wave
            phase = (t * freq) % 1.0
            val = (4.0 * abs(phase - 0.5) - 1.0) * 0.35
            return val * (1.0 - (t / dur) * 0.4)
        return self._build_sound(gen, 0.4)

    def _synth_troll(self):
        # High squeak alert when a trap triggers
        def gen(t, dur):
            freq = 880 - (t / dur) * 400
            phase = (t * freq) % 1.0
            val = 0.25 if phase < 0.5 else -0.25
            return val * (1.0 - t / dur)
        return self._build_sound(gen, 0.08)

    def play(self, sound_name):
        if not self.enabled:
            return
        snd = getattr(self, f"{sound_name}_sfx", None)
        if snd:
            snd.play()


# ==========================================
# PARTICLE SYSTEM
# ==========================================
class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        # Explosive radial burst
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2.5, 7.5)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - random.uniform(1.0, 3.0)
        self.color = random.choice(PARTICLE_COLORS)
        self.size = random.uniform(3.5, 7.0)
        self.life = 1.0
        self.decay = random.uniform(0.02, 0.045)
        self.shape = random.choice(["circle", "star", "sparkle"])
        self.rotation = random.uniform(0, 360)
        self.rot_speed = random.uniform(-10, 10)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2  # Particle gravity
        self.vx *= 0.98  # Air drag
        self.life -= self.decay
        self.rotation += self.rot_speed
        self.size = max(0.5, self.size * 0.97)

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = int(self.life * 255)
        pos = (int(self.x), int(self.y))
        
        if self.shape == "circle":
            surf = pygame.Surface((int(self.size * 2), int(self.size * 2)), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*self.color, alpha), (int(self.size), int(self.size)), int(self.size))
            surface.blit(surf, (pos[0] - self.size, pos[1] - self.size))

        elif self.shape == "star" or self.shape == "sparkle":
            # 4-pointed sparkle
            s = self.size * 1.6
            surf = pygame.Surface((int(s * 2), int(s * 2)), pygame.SRCALPHA)
            c = (*self.color, alpha)
            mid = int(s)
            pts = [
                (mid, mid - s), (mid + s * 0.3, mid),
                (mid, mid + s), (mid - s * 0.3, mid)
            ]
            pygame.draw.polygon(surf, c, pts)
            pts_h = [
                (mid - s, mid), (mid, mid + s * 0.3),
                (mid + s, mid), (mid, mid - s * 0.3)
            ]
            pygame.draw.polygon(surf, c, pts_h)
            surface.blit(surf, (pos[0] - s, pos[1] - s))


class ParticleManager:
    def __init__(self):
        self.particles = []

    def burst(self, x, y, count=40):
        for _ in range(count):
            self.particles.append(Particle(x, y))

    def update(self):
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.life > 0]

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)


# ==========================================
# CUTE CHARACTER RENDERER
# ==========================================
def draw_cute_character(surface, x, y, facing_right=True, is_moving=False, is_jumping=False, anim_timer=0):
    """Draws a cute chibi girl with pastel hair, swaying twin tails, and blushing cheeks."""
    bob = math.sin(anim_timer * 0.2) * 2 if (is_moving and not is_jumping) else 0
    py = y + bob
    flip = 1 if facing_right else -1
    center_x = x + 16

    # 1. Back Hair / Twin Tails
    hair_color = (255, 150, 180)
    bow_color = (255, 80, 120)
    tail_sway = math.sin(anim_timer * 0.15) * 3
    pygame.draw.circle(surface, hair_color, (int(center_x - 12 * flip), int(py - 10 + tail_sway)), 7)
    pygame.draw.circle(surface, hair_color, (int(center_x + 12 * flip), int(py - 10 - tail_sway)), 7)
    
    # Hair Bows
    pygame.draw.circle(surface, bow_color, (int(center_x - 10 * flip), int(py - 12)), 4)
    pygame.draw.circle(surface, bow_color, (int(center_x + 10 * flip), int(py - 12)), 4)

    # 2. Dress / Body
    dress_color = (130, 205, 255)
    dress_points = [
        (center_x - 7, py + 2),
        (center_x + 7, py + 2),
        (center_x + 11, py + 18),
        (center_x - 11, py + 18)
    ]
    pygame.draw.polygon(surface, dress_color, dress_points)
    pygame.draw.polygon(surface, (255, 255, 255), [
        (center_x - 4, py + 2), (center_x + 4, py + 2),
        (center_x + 6, py + 10), (center_x - 6, py + 10)
    ])

    # 3. Legs / Shoes
    shoe_color = (70, 50, 60)
    sock_color = (255, 255, 255)
    leg_offset = math.sin(anim_timer * 0.3) * 4 if (is_moving and not is_jumping) else 0
    
    pygame.draw.rect(surface, sock_color, (center_x - 6, py + 18, 4, 8 - leg_offset))
    pygame.draw.rect(surface, shoe_color, (center_x - 7, py + 24 - leg_offset, 6, 4))
    pygame.draw.rect(surface, sock_color, (center_x + 2, py + 18, 4, 8 + leg_offset))
    pygame.draw.rect(surface, shoe_color, (center_x + 1, py + 24 + leg_offset, 6, 4))

    # 4. Head & Face
    skin_color = (255, 230, 215)
    pygame.draw.circle(surface, skin_color, (int(center_x), int(py - 6)), 12)

    # Hair bangs
    pygame.draw.ellipse(surface, hair_color, (center_x - 13, py - 20, 26, 16))
    pygame.draw.circle(surface, hair_color, (int(center_x - 8 * flip), int(py - 12)), 6)
    pygame.draw.circle(surface, hair_color, (int(center_x + 8 * flip), int(py - 12)), 6)

    # Anime Eyes & Blush
    eye_x1 = center_x + (2 if facing_right else -6)
    eye_x2 = center_x + (7 if facing_right else -1)
    
    blush_color = (255, 160, 170)
    pygame.draw.circle(surface, blush_color, (int(center_x - 7 * flip), int(py - 3)), 3)
    pygame.draw.circle(surface, blush_color, (int(center_x + 7 * flip), int(py - 3)), 3)

    pygame.draw.ellipse(surface, (40, 30, 50), (eye_x1, py - 9, 4, 6))
    pygame.draw.ellipse(surface, (40, 30, 50), (eye_x2, py - 9, 4, 6))
    pygame.draw.circle(surface, (255, 255, 255), (int(eye_x1 + 1), int(py - 8)), 1)
    pygame.draw.circle(surface, (255, 255, 255), (int(eye_x2 + 1), int(py - 8)), 1)

    # Mouth
    pygame.draw.arc(surface, (200, 80, 90), (center_x + (2 * flip) - 2, py - 4, 4, 3), math.pi, 2 * math.pi, 1)


# ==========================================
# LEVEL ELEMENTS & TRAPS
# ==========================================
class Spike:
    def __init__(self, x, y, width=30, height=24, inverted=False, hidden=False):
        self.rect = pygame.Rect(x, y, width, height)
        self.inverted = inverted
        self.hidden = hidden
        self.triggered = False

    def draw(self, surface):
        if self.hidden and not self.triggered:
            return
        points = [
            (self.rect.left, self.rect.bottom if not self.inverted else self.rect.top),
            (self.rect.right, self.rect.bottom if not self.inverted else self.rect.top),
            (self.rect.centerx, self.rect.top if not self.inverted else self.rect.bottom)
        ]
        pygame.draw.polygon(surface, COLOR_SPIKE, points)
        pygame.draw.polygon(surface, (255, 120, 140), points, 2)


class Platform:
    def __init__(self, x, y, width, height, is_fake=False, collapses=False, moves=False, move_range=(0, 0)):
        self.rect = pygame.Rect(x, y, width, height)
        self.original_rect = pygame.Rect(x, y, width, height)
        self.is_fake = is_fake
        self.collapses = collapses
        self.collapsed = False
        self.collapse_speed = 0
        self.moves = moves
        self.move_range = move_range
        self.move_dir = 1
        self.color = COLOR_PLATFORM

    def update(self):
        if self.collapses and self.collapsed:
            self.collapse_speed += 0.5
            self.rect.y += int(self.collapse_speed)
        
        if self.moves:
            self.rect.x += self.move_dir * 2
            if self.rect.x > self.original_rect.x + self.move_range[1] or self.rect.x < self.original_rect.x - self.move_range[0]:
                self.move_dir *= -1

    def draw(self, surface):
        if self.is_fake and self.collapsed:
            return
        pygame.draw.rect(surface, self.color, self.rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_PLATFORM_ACCENT, self.rect, width=3, border_radius=6)


class Door:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 36, 54)

    def update(self, player_rect, troll_type=None, sfx=None):
        if troll_type == "runaway":
            dist = math.hypot(self.rect.centerx - player_rect.centerx, self.rect.centery - player_rect.centery)
            if dist < 120:
                if self.rect.x < SCREEN_WIDTH - 60 and sfx and random.random() < 0.05:
                    sfx.play("troll")
                self.rect.x = min(SCREEN_WIDTH - 60, self.rect.x + 4)
        elif troll_type == "jump_over":
            if abs(self.rect.centerx - player_rect.centerx) < 100:
                self.rect.y = max(100, self.rect.y - 8)

    def draw(self, surface):
        pygame.draw.rect(surface, COLOR_DOOR, self.rect, border_radius=8)
        pygame.draw.rect(surface, COLOR_DOOR_INNER, self.rect.inflate(-8, -8), border_radius=4)
        pygame.draw.circle(surface, (80, 50, 20), (self.rect.right - 8, self.rect.centery), 3)


# ==========================================
# STAGE BLUEPRINTS
# ==========================================
def get_level(stage_num):
    platforms = []
    spikes = []
    player_spawn = (60, 480)
    door = Door(710, 466)
    traps = {}

    if stage_num == 1:
        # STAGE 1: Collapsing central bridge
        platforms.append(Platform(0, 520, 250, 80))
        platforms.append(Platform(270, 520, 260, 80, collapses=True))
        platforms.append(Platform(550, 520, 250, 80))
        traps["collapse_trigger_x"] = 230

    elif stage_num == 2:
        # STAGE 2: Runaway door & ambush spikes
        platforms.append(Platform(0, 520, 800, 80))
        platforms.append(Platform(250, 380, 140, 20))
        platforms.append(Platform(450, 260, 140, 20))
        spikes.append(Spike(320, 496, hidden=True))
        spikes.append(Spike(480, 496, hidden=True))
        traps["door_troll"] = "runaway"

    elif stage_num == 3:
        # STAGE 3: Inverted controls & dropping ceiling
        platforms.append(Platform(0, 520, 800, 80))
        platforms.append(Platform(200, 400, 80, 20))
        platforms.append(Platform(360, 310, 80, 20))
        platforms.append(Platform(520, 400, 80, 20))

        spikes.append(Spike(200, 520 - 24))
        spikes.append(Spike(360, 520 - 24))
        spikes.append(Spike(520, 520 - 24))
        
        ceiling_trap = Platform(280, -40, 240, 30, collapses=True)
        platforms.append(ceiling_trap)
        traps["invert_controls_x"] = 300
        traps["falling_ceiling"] = ceiling_trap

    elif stage_num == 4:
        # STAGE 4: Full spike field with floating platforms
        platforms.append(Platform(0, 520, 120, 80))
        platforms.append(Platform(680, 520, 120, 80))
        for sx in range(120, 680, 30):
            spikes.append(Spike(sx, 520))
        platforms.extend([
            Platform(200, 420, 90, 20),
            Platform(360, 320, 90, 20),
            Platform(520, 240, 90, 20)
        ])
        traps["door_troll"] = "jump_over"

    return platforms, spikes, door, player_spawn, traps


# ==========================================
# MAIN LOOP
# ==========================================
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Level Devil - Kawaii Edition ✨")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 22, bold=True)
    title_font = pygame.font.SysFont("Arial", 36, bold=True)

    sfx = SoundFX()
    particles = ParticleManager()

    current_stage = 1
    total_stages = 4
    deaths = 0

    def reset_level(stage_idx):
        return get_level(stage_idx)

    platforms, spikes, door, spawn_pos, traps = reset_level(current_stage)
    
    px, py = float(spawn_pos[0]), float(spawn_pos[1])
    vx, vy = 0.0, 0.0
    is_grounded = False
    facing_right = True
    anim_timer = 0
    inverted_controls = False
    won_game = False
    death_timer = 0

    while True:
        clock.tick(FPS)
        anim_timer += 1

        # ----------------------------------
        # 1. INPUT PROCESSING
        # ----------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    deaths += 1
                    sfx.play("death")
                    particles.burst(px + 13, py - 12, count=35)
                    death_timer = 20

        keys = pygame.key.get_pressed()
        
        # Dead delay handling (allows particle explosion to show before resetting)
        if death_timer > 0:
            death_timer -= 1
            if death_timer == 0:
                platforms, spikes, door, spawn_pos, traps = reset_level(current_stage)
                px, py = float(spawn_pos[0]), float(spawn_pos[1])
                vx, vy = 0, 0
                inverted_controls = False
        else:
            move_left = keys[pygame.K_LEFT] or keys[pygame.K_a]
            move_right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
            jump_pressed = keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]

            if "invert_controls_x" in traps and px > traps["invert_controls_x"] and not inverted_controls:
                inverted_controls = True
                sfx.play("troll")
                
            if inverted_controls:
                move_left, move_right = move_right, move_left

            vx = 0
            if move_left:
                vx = -PLAYER_SPEED
                facing_right = False
            if move_right:
                vx = PLAYER_SPEED
                facing_right = True

            if jump_pressed and is_grounded:
                vy = JUMP_FORCE
                is_grounded = False
                sfx.play("jump")

            # ----------------------------------
            # 2. TRAP TRIGGERS
            # ----------------------------------
            player_rect = pygame.Rect(int(px), int(py - 24), 26, 32)

            # Collapse trap
            if "collapse_trigger_x" in traps and px > traps["collapse_trigger_x"]:
                for p in platforms:
                    if p.collapses and not p.collapsed:
                        p.collapsed = True
                        sfx.play("troll")

            # Falling ceiling trap
            if "falling_ceiling" in traps and px > 260 and not traps["falling_ceiling"].collapsed:
                traps["falling_ceiling"].collapsed = True
                sfx.play("troll")

            # Hidden Spikes
            for s in spikes:
                if s.hidden and not s.triggered and abs(s.rect.centerx - player_rect.centerx) < 70:
                    s.triggered = True
                    sfx.play("troll")

            # Door Troll AI
            door.update(player_rect, traps.get("door_troll", None), sfx)

            # ----------------------------------
            # 3. PHYSICS & COLLISION
            # ----------------------------------
            vy = min(14.0, vy + GRAVITY)

            # Horizontal movement & collision
            px += vx
            player_rect.x = int(px)
            for p in platforms:
                p.update()
                if not p.is_fake and player_rect.colliderect(p.rect):
                    if vx > 0:
                        player_rect.right = p.rect.left
                    elif vx < 0:
                        player_rect.left = p.rect.right
                    px = float(player_rect.x)

            # Vertical movement & collision
            py += vy
            player_rect.y = int(py - 24)
            is_grounded = False

            for p in platforms:
                if not p.is_fake and player_rect.colliderect(p.rect):
                    if vy > 0 and player_rect.bottom - vy <= p.rect.top + 10:
                        player_rect.bottom = p.rect.top
                        py = float(player_rect.bottom)
                        vy = 0
                        is_grounded = True
                    elif vy < 0:
                        player_rect.top = p.rect.bottom
                        py = float(player_rect.bottom)
                        vy = 0

            # Death Checks
            dead = False
            for s in spikes:
                if (not s.hidden or s.triggered) and player_rect.colliderect(s.rect):
                    dead = True
            if py > SCREEN_HEIGHT + 50:
                dead = True

            if dead:
                deaths += 1
                sfx.play("death")
                particles.burst(px + 13, py - 12, count=45)
                death_timer = 25
                continue

            # Stage Win Collision
            if player_rect.colliderect(door.rect):
                sfx.play("win")
                if current_stage < total_stages:
                    current_stage += 1
                    platforms, spikes, door, spawn_pos, traps = reset_level(current_stage)
                    px, py = float(spawn_pos[0]), float(spawn_pos[1])
                    vx, vy = 0, 0
                    inverted_controls = False
                else:
                    won_game = True

        # Particle Update
        particles.update()

        # ----------------------------------
        # 4. RENDERING
        # ----------------------------------
        screen.fill(COLOR_BG)

        for p in platforms:
            p.draw(screen)
        for s in spikes:
            s.draw(screen)
        door.draw(screen)

        # Draw particles behind/around character
        particles.draw(screen)

        # Draw character if alive
        if death_timer == 0 and not won_game:
            draw_cute_character(
                screen, 
                int(px) - 3, 
                int(py) - 26, 
                facing_right=facing_right, 
                is_moving=(vx != 0), 
                is_jumping=(not is_grounded), 
                anim_timer=anim_timer
            )

        # HUD & UI
        stage_text = font.render(f"Stage: {current_stage}/{total_stages}", True, COLOR_TEXT)
        death_text = font.render(f"Fails: {deaths}", True, (220, 70, 90))
        screen.blit(stage_text, (20, 20))
        screen.blit(death_text, (20, 50))

        if inverted_controls and death_timer == 0:
            inv_text = font.render("⚠ CONTROLS REVERSED! ⚠", True, (200, 50, 80))
            screen.blit(inv_text, (SCREEN_WIDTH // 2 - inv_text.get_width() // 2, 20))

        if won_game:
            win_msg = title_font.render("✨ YOU BEAT THE TROLLS! ✨", True, (100, 180, 90))
            sub_msg = font.render(f"Total Fails: {deaths} | Press 'R' to Play Again", True, COLOR_TEXT)
            screen.blit(win_msg, (SCREEN_WIDTH // 2 - win_msg.get_width() // 2, SCREEN_HEIGHT // 2 - 40))
            screen.blit(sub_msg, (SCREEN_WIDTH // 2 - sub_msg.get_width() // 2, SCREEN_HEIGHT // 2 + 10))

        pygame.display.flip()

if __name__ == "__main__":
    main()