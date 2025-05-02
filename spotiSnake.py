import pygame 
import time
import random

snake_speed = 17

width = 720
height = 720

black = pygame.Color(0, 0, 0)
white = pygame.Color(255, 255, 255)
red = pygame.Color(255, 0, 0)
green = pygame.Color(0, 255, 0)
blue = pygame.Color(0, 0, 255)

pygame.init()
pygame.display.set_caption('spoti-snake')
snake_field = pygame.display.set_mode((width,height))

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
    pygame.quit()
    quit()

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