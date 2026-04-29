import arcade
import math
import random
import time
import os
import json

# ---------- Constants ----------
SCREEN_WIDTH = fullscreen_width = arcade.get_display_size()[0]
SCREEN_HEIGHT = fullscreen_height = arcade.get_display_size()[1]
SCREEN_TITLE = "Space Shooter"

PLAYER_START_HEALTH = 100
BULLET_SPEED = 18
ENEMY_BASE_SPEED = 1.5
DIFFICULTY_SCALING = 0.1
POWERUP_CHANCE = 0.15
POWERUP_DURATION = 8.0
PLAYER_IMAGE_ANGLE_OFFSET = -90

HIGH_SCORE_FILE = "highscore.json"


# ---------- Player ----------
class Player(arcade.Sprite):
    def __init__(self):
        super().__init__("player.png", scale=0.50)

        self.center_x = SCREEN_WIDTH // 2
        self.center_y = SCREEN_HEIGHT // 2

        self.angle = 0
        self.health = PLAYER_START_HEALTH

        self.speed = 9
        self.acceleration = 0.8
        self.friction = 0.85

        self.velocity_x = 0
        self.velocity_y = 0

        self.move_x = 0
        self.move_y = 0

        self.keys_pressed = {
            "up": False,
            "down": False,
            "left": False,
            "right": False
        }

    def update(self, delta_time=1 / 60):
        input_magnitude = math.sqrt(self.move_x ** 2 + self.move_y ** 2)

        if input_magnitude > 0:
            normalized_x = self.move_x / input_magnitude
            normalized_y = self.move_y / input_magnitude
        else:
            normalized_x = 0
            normalized_y = 0

        self.velocity_x += normalized_x * self.acceleration
        self.velocity_y += normalized_y * self.acceleration

        self.velocity_x *= self.friction
        self.velocity_y *= self.friction

        speed = math.sqrt(self.velocity_x ** 2 + self.velocity_y ** 2)
        if speed > self.speed:
            ratio = self.speed / speed
            self.velocity_x *= ratio
            self.velocity_y *= ratio

        self.center_x += self.velocity_x
        self.center_y += self.velocity_y

        self.center_x = max(25, min(self.center_x, SCREEN_WIDTH - 25))
        self.center_y = max(25, min(self.center_y, SCREEN_HEIGHT - 25))


# ---------- Enemy ----------
class Enemy(arcade.Sprite):
    def __init__(self, level, enemy_type="normal"):
        if enemy_type == "boss":
            super().__init__("alien.png", scale=0.35)
            self.is_boss = True
            self.health = 4
            self.max_health = 4
        elif enemy_type == "fast":
            super().__init__("alien.png", scale=0.50)
            self.is_boss = False
            self.health = 1
            self.max_health = 1
        elif enemy_type == "shooter":
            super().__init__("alien.png", scale=0.20)
            self.is_boss = False
            self.health = 2
            self.max_health = 2
        elif enemy_type == "zigzag":
            super().__init__("enemy.png", scale=0.20)
            self.is_boss = False
            self.health = 1
            self.max_health = 1
        elif enemy_type == "tank":
            super().__init__("enemy.png", scale=0.32)
            self.is_boss = False
            self.health = 4
            self.max_health = 4
        else:
            super().__init__("enemy.png", scale=0.20)
            self.is_boss = False
            self.health = 1
            self.max_health = 1

        self.enemy_type = enemy_type
        self.last_shot_time = time.time()
        self.zigzag_offset = random.uniform(0, math.pi * 2)

        while True:
            self.center_x = random.randint(0, SCREEN_WIDTH)
            self.center_y = random.randint(0, SCREEN_HEIGHT)
            if math.hypot(self.center_x - SCREEN_WIDTH // 2, self.center_y - SCREEN_HEIGHT // 2) > 150:
                break

        base_speed = ENEMY_BASE_SPEED
        if enemy_type == "boss":
            base_speed = ENEMY_BASE_SPEED * 0.7
        elif enemy_type == "fast":
            base_speed = ENEMY_BASE_SPEED * 1.5
        elif enemy_type == "tank":
            base_speed = ENEMY_BASE_SPEED * 0.6
        elif enemy_type == "shooter":
            base_speed = ENEMY_BASE_SPEED * 1.0
        else:
            base_speed = ENEMY_BASE_SPEED

        self.speed = base_speed + (level - 1) * DIFFICULTY_SCALING

    def update(self, player, delta_time=1 / 60):
        dx = player.center_x - self.center_x
        dy = player.center_y - self.center_y
        angle = math.atan2(dy, dx)

        if self.enemy_type == "zigzag":
            self.center_x += math.cos(angle) * self.speed
            self.center_y += math.sin(angle) * self.speed + math.sin(time.time() * 5 + self.zigzag_offset) * 2
        else:
            self.center_x += math.cos(angle) * self.speed
            self.center_y += math.sin(angle) * self.speed

    def maybe_shoot(self, player):
        if self.enemy_type != "shooter":
            return None

        current_time = time.time()
        shoot_delay = max(1.4 - self.speed * 0.1, 0.8)
        if current_time - self.last_shot_time < shoot_delay:
            return None

        self.last_shot_time = current_time
        dx = player.center_x - self.center_x
        dy = player.center_y - self.center_y
        angle = math.degrees(math.atan2(dy, dx))
        return Bullet(self.center_x, self.center_y, angle)

    def take_damage(self):
        self.health -= 1
        return self.health <= 0


# ---------- Bullet ----------
class Bullet(arcade.Sprite):
    def __init__(self, x, y, angle):
        super().__init__("bullet.png", scale=0.04)  # Made smaller

        self.center_x = x
        self.center_y = y
        self.angle = angle

        self.change_x = math.cos(math.radians(angle)) * BULLET_SPEED
        self.change_y = math.sin(math.radians(angle)) * BULLET_SPEED

    def update(self, delta_time=1 / 60):
        self.center_x += self.change_x
        self.center_y += self.change_y

        if (
            self.center_x < 0 or self.center_x > SCREEN_WIDTH or
            self.center_y < 0 or self.center_y > SCREEN_HEIGHT
        ):
            self.remove_from_sprite_lists()


# ---------- Power-Up ----------
class PowerUp(arcade.Sprite):
    def __init__(self, x, y, powerup_type):
        texture = arcade.make_soft_circle_texture(24, arcade.color.GOLD, 255, 0.8)
        super().__init__(texture, scale=3.0)
        self.center_x = x
        self.center_y = y
        self.powerup_type = powerup_type
        self.change_x = random.uniform(-0.5, 0.5)
        self.change_y = random.uniform(-0.5, 0.5)

    def update(self, delta_time=1 / 60):
        self.center_x += self.change_x
        self.center_y += self.change_y

        if (
            self.center_x < 0 or self.center_x > SCREEN_WIDTH or
            self.center_y < 0 or self.center_y > SCREEN_HEIGHT
        ):
            self.remove_from_sprite_lists()


class Explosion:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.time_started = time.time()
        self.duration = 0.35

    def update(self):
        return time.time() - self.time_started < self.duration

    def draw(self):
        progress = (time.time() - self.time_started) / self.duration
        radius = 12 + progress * 18
        alpha = int(255 * (1 - progress))
        arcade.draw_circle_filled(self.x, self.y, radius, (255, 140, 0, alpha))


# ---------- High Score ----------
def load_high_score():
    try:
        if os.path.exists(HIGH_SCORE_FILE):
            with open(HIGH_SCORE_FILE, "r") as f:
                data = json.load(f)
                return data.get("high_score", 0)
    except:
        pass
    return 0


def save_high_score(score):
    try:
        with open(HIGH_SCORE_FILE, "w") as f:
            json.dump({"high_score": score}, f)
    except:
        pass


def load_sound(filename):
    try:
        if os.path.exists(filename):
            return arcade.load_sound(filename)
    except:
        pass
    return None


# ---------- Game ----------
class GameView(arcade.View):
    def __init__(self):
        super().__init__()

        self.player_list = arcade.SpriteList()
        self.enemy_list = arcade.SpriteList()
        self.bullet_list = arcade.SpriteList()
        self.background_list = arcade.SpriteList()

        self.player = None
        self.score = 0
        self.level = 1
        self.game_over = False
        self.kill_streak = 0
        self.last_kill_time = 0
        self.high_score = load_high_score()
        self.level_start_time = time.time()
        self.enemies_spawned_this_level = 0

        self.last_shot_time = 0
        self.shoot_delay = 0.08  # Faster shooting for continuous fire
        self.shooting_mouse = False
        self.shooting_space = False

        self.mouse_x = SCREEN_WIDTH // 2
        self.mouse_y = SCREEN_HEIGHT // 2

        self.player_name = "Player1"
        self.powerup_list = arcade.SpriteList()
        self.powerup_active = False
        self.powerup_type = None
        self.powerup_end_time = 0
        self.explosion_list = []
        self.shoot_sound = None
        self.explosion_sound = None
        self.powerup_sound = None

    def setup(self):
        self.player_list = arcade.SpriteList()
        self.enemy_list = arcade.SpriteList()
        self.bullet_list = arcade.SpriteList()
        self.background_list = arcade.SpriteList()

        self.player = Player()
        self.player_list.append(self.player)

        self.load_background()

        self.shoot_sound = load_sound("shoot.wav")
        self.explosion_sound = load_sound("explosion.wav")
        self.powerup_sound = load_sound("powerup.wav")

        self.score = 0
        self.level = 1
        self.game_over = False
        self.kill_streak = 0
        self.last_kill_time = 0
        self.level_start_time = time.time()
        self.enemies_spawned_this_level = 0
        self.last_shot_time = 0
        self.powerup_list = arcade.SpriteList()
        self.powerup_active = False
        self.powerup_type = None
        self.powerup_end_time = 0

        self.spawn_level_enemies()

    def spawn_level_enemies(self):
        self.enemies_spawned_this_level = 0

        base_count = 5 + self.level

        if self.level % 5 == 0:
            boss_count = max(1, self.level // 5)
            for _ in range(boss_count):
                enemy = Enemy(self.level, "boss")
                self.enemy_list.append(enemy)
                self.enemies_spawned_this_level += 1

            fast_count = min(3, self.level // 3)
            for _ in range(fast_count):
                enemy = Enemy(self.level, "fast")
                self.enemy_list.append(enemy)
                self.enemies_spawned_this_level += 1

            shooter_count = min(2, self.level // 4)
            for _ in range(shooter_count):
                enemy = Enemy(self.level, "shooter")
                self.enemy_list.append(enemy)
                self.enemies_spawned_this_level += 1
        else:
            tank_count = 1 if self.level > 4 else 0
            zigzag_count = min(2, self.level // 3) if self.level > 3 else 0
            shooter_count = min(2, self.level // 4) if self.level > 2 else 0
            fast_count = min(2, self.level // 3)
            normal_count = max(1, base_count - tank_count - zigzag_count - shooter_count - fast_count)

            for _ in range(normal_count):
                enemy = Enemy(self.level, "normal")
                self.enemy_list.append(enemy)
                self.enemies_spawned_this_level += 1

            for _ in range(fast_count):
                enemy = Enemy(self.level, "fast")
                self.enemy_list.append(enemy)
                self.enemies_spawned_this_level += 1

            for _ in range(zigzag_count):
                enemy = Enemy(self.level, "zigzag")
                self.enemy_list.append(enemy)
                self.enemies_spawned_this_level += 1

            for _ in range(shooter_count):
                enemy = Enemy(self.level, "shooter")
                self.enemy_list.append(enemy)
                self.enemies_spawned_this_level += 1

            for _ in range(tank_count):
                enemy = Enemy(self.level, "tank")
                self.enemy_list.append(enemy)
                self.enemies_spawned_this_level += 1

    def update_aim(self, x, y):
        self.mouse_x = x
        self.mouse_y = y

        dx = x - self.player.center_x
        dy = y - self.player.center_y
        base_angle = math.degrees(math.atan2(dy, dx))
        self.player.angle = base_angle + PLAYER_IMAGE_ANGLE_OFFSET

    def load_background(self):
        self.background_list = arcade.SpriteList()
        if self.level < 5:
            bg_file = "background1.png"
        else:
            bg_file = "background2.png"

        if not os.path.exists(bg_file):
            bg_file = "background.png"

        background = arcade.Sprite(bg_file)
        background.center_x = SCREEN_WIDTH // 2
        background.center_y = SCREEN_HEIGHT // 2
        background.scale = max(
            SCREEN_WIDTH / background.width,
            SCREEN_HEIGHT / background.height
        )
        self.background_list.append(background)

    def fire_bullet(self, target_x, target_y):
        current_time = time.time()
        effective_delay = self.shoot_delay * (0.5 if self.powerup_type == "rapid" else 1.0)
        if current_time - self.last_shot_time < effective_delay:
            return

        dx = target_x - self.player.center_x
        dy = target_y - self.player.center_y
        base_angle = math.degrees(math.atan2(dy, dx))

        # Spawn bullets in front of the ship
        offset_distance = max(self.player.width, self.player.height) * 0.4
        spawn_x = self.player.center_x + math.cos(math.radians(base_angle)) * offset_distance
        spawn_y = self.player.center_y + math.sin(math.radians(base_angle)) * offset_distance

        # Add bullet spread (±5 degrees)
        spread_angle = base_angle + random.uniform(-5, 5)

        if self.powerup_type == "triple":
            for extra_angle in (-6, 0, 6):
                bullet = Bullet(spawn_x, spawn_y, spread_angle + extra_angle)
                self.bullet_list.append(bullet)
        else:
            bullet = Bullet(spawn_x, spawn_y, spread_angle)
            self.bullet_list.append(bullet)

        if self.shoot_sound:
            arcade.play_sound(self.shoot_sound)

        self.last_shot_time = current_time

    def on_draw(self):
        self.clear()
        self.background_list.draw()

        if not self.game_over:
            self.player_list.draw()
            self.enemy_list.draw()
            self.bullet_list.draw()
            self.powerup_list.draw()
            for explosion in list(self.explosion_list):
                explosion.draw()

            arcade.draw_text(f"Player: {self.player_name}", 10, 10, arcade.color.WHITE, 14)
            arcade.draw_text(f"Score: {self.score}", 10, 30, arcade.color.WHITE, 14)
            arcade.draw_text(f"High Score: {self.high_score}", 10, 50, arcade.color.YELLOW, 14)
            arcade.draw_text(f"Health: {self.player.health}", 10, 70, arcade.color.RED, 14)
            arcade.draw_text(f"Level: {self.level}", 10, 90, arcade.color.CYAN, 14)

            if self.kill_streak > 1:
                arcade.draw_text(f"Combo: {self.kill_streak}x", 10, 90, arcade.color.ORANGE, 14)

            if self.powerup_active and self.powerup_type:
                arcade.draw_text(
                    f"Power-Up: {self.powerup_type.upper()} ({int(self.powerup_end_time - time.time())}s)",
                    10,
                    110,
                    arcade.color.LIME_GREEN,
                    14
                )

            enemy_count = len(self.enemy_list)
            arcade.draw_text(f"Enemies: {enemy_count}", SCREEN_WIDTH - 120, 10, arcade.color.WHITE, 14)

            level_time = int(time.time() - self.level_start_time)
            arcade.draw_text(f"Time: {level_time}s", SCREEN_WIDTH - 120, 30, arcade.color.GREEN, 14)

            arcade.draw_circle_outline(self.mouse_x, self.mouse_y, 12, arcade.color.RED, 2)
        else:
            arcade.draw_text(
                "GAME OVER",
                SCREEN_WIDTH // 2 - 100,
                SCREEN_HEIGHT // 2 + 50,
                arcade.color.RED,
                30
            )
            arcade.draw_text(
                f"Final Score: {self.score}",
                SCREEN_WIDTH // 2 - 80,
                SCREEN_HEIGHT // 2 + 10,
                arcade.color.WHITE,
                20
            )
            arcade.draw_text(
                f"High Score: {self.high_score}",
                SCREEN_WIDTH // 2 - 75,
                SCREEN_HEIGHT // 2 - 20,
                arcade.color.YELLOW,
                20
            )
            arcade.draw_text(
                f"Level Reached: {self.level}",
                SCREEN_WIDTH // 2 - 85,
                SCREEN_HEIGHT // 2 - 50,
                arcade.color.CYAN,
                20
            )
            arcade.draw_text(
                "Press R to Restart",
                SCREEN_WIDTH // 2 - 80,
                SCREEN_HEIGHT // 2 - 100,
                arcade.color.GREEN,
                16
            )

    def on_update(self, delta_time):
        if self.game_over:
            return

        self.player_list.update()
        self.bullet_list.update()
        self.powerup_list.update()

        self.explosion_list = [explosion for explosion in self.explosion_list if explosion.update()]

        if self.powerup_active and time.time() >= self.powerup_end_time:
            self.powerup_active = False
            self.powerup_type = None

        if self.shooting_mouse or self.shooting_space:
            self.fire_bullet(self.mouse_x, self.mouse_y)

        for enemy in self.enemy_list:
            enemy.update(self.player)
            bullet = enemy.maybe_shoot(self.player)
            if bullet:
                self.bullet_list.append(bullet)

        for bullet in list(self.bullet_list):
            hit_list = arcade.check_for_collision_with_list(bullet, self.enemy_list)
            if hit_list:
                bullet.remove_from_sprite_lists()

                enemy = hit_list[0]
                if enemy.take_damage():
                    enemy.remove_from_sprite_lists()

                    base_points = 10 if enemy.is_boss else 5
                    current_time = time.time()

                    if current_time - self.last_kill_time < 2.0:
                        self.kill_streak += 1
                    else:
                        self.kill_streak = 1

                    combo_multiplier = 1 + (self.kill_streak - 1) * 0.5
                    total_points = int(base_points * self.level * combo_multiplier)

                    self.score += total_points
                    self.last_kill_time = current_time
                    self.explosion_list.append(Explosion(enemy.center_x, enemy.center_y))
                    if self.explosion_sound:
                        arcade.play_sound(self.explosion_sound)

                    if random.random() < POWERUP_CHANCE:
                        powerup_type = random.choice(["rapid", "triple"])
                        powerup = PowerUp(enemy.center_x, enemy.center_y, powerup_type)
                        self.powerup_list.append(powerup)

        hit_list = arcade.check_for_collision_with_list(self.player, self.enemy_list)
        for enemy in hit_list:
            enemy.remove_from_sprite_lists()
            self.player.health -= 10

        powerup_hits = arcade.check_for_collision_with_list(self.player, self.powerup_list)
        for powerup in powerup_hits:
            powerup.remove_from_sprite_lists()
            self.powerup_active = True
            self.powerup_type = powerup.powerup_type
            self.powerup_end_time = time.time() + POWERUP_DURATION
            if self.powerup_sound:
                arcade.play_sound(self.powerup_sound)

        if self.player.health <= 0:
            self.game_over = True
            if self.score > self.high_score:
                self.high_score = self.score
                save_high_score(self.high_score)

        if len(self.enemy_list) == 0 and not self.game_over:
            self.level += 1
            self.level_start_time = time.time()
            self.load_background()
            self.spawn_level_enemies()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.W:
            self.player.keys_pressed["up"] = True
        elif key == arcade.key.S:
            self.player.keys_pressed["down"] = True
        elif key == arcade.key.A:
            self.player.keys_pressed["left"] = True
        elif key == arcade.key.D:
            self.player.keys_pressed["right"] = True
        elif key == arcade.key.SPACE:
            self.shooting_space = True
            self.fire_bullet(self.mouse_x, self.mouse_y)
        elif key == arcade.key.BACKSPACE:
            self.player_name = self.player_name[:-1]
        elif key == arcade.key.R and self.game_over:
            self.setup()
        elif 32 <= key <= 126:
            self.player_name += chr(key)

        self.update_movement_directions()

    def on_key_release(self, key, modifiers):
        if key == arcade.key.W:
            self.player.keys_pressed["up"] = False
        elif key == arcade.key.S:
            self.player.keys_pressed["down"] = False
        elif key == arcade.key.A:
            self.player.keys_pressed["left"] = False
        elif key == arcade.key.D:
            self.player.keys_pressed["right"] = False
        elif key == arcade.key.SPACE:
            self.shooting_space = False

        self.update_movement_directions()

    def update_movement_directions(self):
        self.player.move_x = 0
        self.player.move_y = 0

        if self.player.keys_pressed["right"]:
            self.player.move_x += 1
        if self.player.keys_pressed["left"]:
            self.player.move_x -= 1
        if self.player.keys_pressed["up"]:
            self.player.move_y += 1
        if self.player.keys_pressed["down"]:
            self.player.move_y -= 1

    def on_mouse_motion(self, x, y, dx, dy):
        self.update_aim(x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.shooting_mouse = True
            self.update_aim(x, y)
            self.fire_bullet(x, y)  # Fire immediately on press

    def on_mouse_release(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.shooting_mouse = False


# ---------- Main ----------
def main():
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, fullscreen=True)
    game = GameView()
    game.setup()
    window.show_view(game)
    arcade.run()


if __name__ == "__main__":
    main()
