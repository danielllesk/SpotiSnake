import pygame 
import time
import random
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import sys

pygame.init()
width = 720
height = 720
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("SpotiSnake - Start Menu")
clock = pygame.time.Clock()

black = pygame.Color(0, 0, 0)
white = pygame.Color(255, 255, 255)
red = pygame.Color(255, 0, 0)
green = pygame.Color(0, 255, 0)
LIGHT_BLUE = (173, 216, 230)
DARK_BLUE = (0, 0, 139)
BLACK = (0, 0, 0)


font = pygame.font.SysFont("Corbel", 36)

def draw_button(text, x, y, w, h, inactive_color, active_color, action=None):
    mouse = pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()

    if x < mouse[0] < x + w and y < mouse[1] < y + h:
        pygame.draw.rect(screen, active_color, (x, y, w, h))
        if click[0] == 1 and action:
            action()
    else:
        pygame.draw.rect(screen, inactive_color, (x, y, w, h))

    text_surf = font.render(text, True, BLACK)
    text_rect = text_surf.get_rect(center=(x + w // 2, y + h // 2))
    screen.blit(text_surf, text_rect)


def start_game():
    
    pygame.display.set_caption('spoti-snake')
    snake_field = pygame.display.set_mode((width,height))
    snake_speed = 17

    def show_score(choice, colour, font, size):
        score_font = pygame.font.SysFont(font,size)
        score_surface = score_font.render('Score : ' + str(score), True, colour)
        score_rect = score_surface.get_rect()
        snake_field.blit(score_surface,score_rect)
    def game_over():
        my_font = pygame.font.SysFont('times new roman', 50)
        game_over_surface = my_font.render('Your Score is : ' + str(score), True, red)
        game_over_rect = game_over_surface.get_rect()
        game_over_rect.midtop = (width/2,height/2)
        snake_field.blit(game_over_surface, game_over_rect)
        pygame.display.flip()
        time.sleep(2)
        start_menu()

    fps = pygame.time.Clock()

    snake_position = [360,360]
    snake_body = [[360,360],
                [350,360],
                [340,360],
                [330,360]]
    fruit_position = [random.randrange(1,(width//10))*10, random.randrange(1,(height//10))*10]

    fruit_spawn = False

    snake_direction = 'RIGHT'
    change_to = snake_direction

    score  = 0
    while True:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    change_to = 'UP'
                if event.key == pygame.K_DOWN:
                    change_to = 'DOWN'
                if event.key == pygame.K_RIGHT:
                    change_to = 'RIGHT'
                if event.key == pygame.K_LEFT:
                    change_to = 'LEFT'
        if change_to == 'UP' and snake_direction != 'DOWN':
            snake_direction = 'UP'
        if change_to == 'DOWN' and snake_direction != 'UP':
            snake_direction = 'DOWN'
        if change_to == 'LEFT' and snake_direction != 'RIGHT':
            snake_direction = 'LEFT'
        if change_to == 'RIGHT' and snake_direction != 'LEFT':
            snake_direction = 'RIGHT'
        
        if snake_direction == 'UP':
            snake_position[1] -= 10
        if snake_direction == 'DOWN':
            snake_position[1] += 10
        if snake_direction == 'RIGHT':
            snake_position[0] += 10
        if snake_direction == 'LEFT':
            snake_position[0] -= 10
        snake_body.insert(0, list(snake_position))

        if snake_position[0] == fruit_position[0] and snake_position[1] == fruit_position[1]:
            score+=10
            fruit_spawn = False
        else:
            snake_body.pop()

        if not fruit_spawn:
            fruit_position = [random.randrange(1,(width//10))*10, random.randrange(1,(height//10))*10]
        fruit_spawn = True
        snake_field.fill(black)

        for pos in snake_body:
            pygame.draw.rect(snake_field, green,pygame.Rect(pos[0],pos[1],10,10))
        pygame.draw.rect(snake_field, white, pygame.Rect(fruit_position[0], fruit_position[1],10,10))
        if snake_position[0] < 0 or snake_position[0] >width-10:
            game_over()
        if snake_position[1] < 0 or snake_position[1]>height- 10:
            game_over()

        show_score(1, white, 'times new roman',20)

        pygame.display.update()

        fps.tick(snake_speed)

def quit_game():
    pygame.quit()
    sys.exit()

def start_menu():
    running = True
    while running:
        screen.fill(white)

        title_text = font.render("Welcome to SpotiSnake", True, DARK_BLUE)
        title_rect = title_text.get_rect(center=(width // 2, 100))
        screen.blit(title_text, title_rect)

        draw_button("Play", 220, 200, 200, 50, LIGHT_BLUE, DARK_BLUE, start_game)
        draw_button("Quit", 220, 280, 200, 50, LIGHT_BLUE, DARK_BLUE, quit_game)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        pygame.display.update()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    start_menu()
