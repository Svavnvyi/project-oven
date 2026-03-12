import pygame

pygame.init()

clock = pygame.time.Clock()
fps = 60

bottom_panel = 160
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 500 + bottom_panel

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Konyhai Karnevál')

background_img = pygame.image.load('pixil-frame-0.png').convert_alpha()

panel_img = pygame.image.load('panL.png').convert_alpha()

def draw_bg():
    screen.blit(background_img, (0, 0))

def draw_panel():
    screen.blit(panel_img, (0, SCREEN_HEIGHT - bottom_panel))

class Fighter():
    def __init__(self, x, y, name, max_hp, strength, status):
        self.name = name
        self.max_hp = max_hp
        self.hp = max_hp
        self.strength = strength
        self.alive = True
        self.animation_list = []
        self.frame_index = 0
        self.action = 1
        self.update_time = pygame.time.get_ticks()
        temp_list = []
        for i in range(3):
            img = pygame.image.load(f'{status}/{self.name}/Idle{i}R.png')
            img = pygame.transform.scale(img, (img.get_width() * 3, img.get_height() * 3 ))
            temp_list.append(img)
        self.animation_list.append(temp_list)
        temp_list = []
        for i in range(16):
            img = pygame.image.load(f'{status}/{self.name}/XFallattack{i}R.png')
            img = pygame.transform.scale(img, (img.get_width(), img.get_height()))
            temp_list.append(img)
        self.animation_list.append(temp_list)
        self.image = self.animation_list[self.action][self.frame_index]
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

    def update(self):
        animation_cooldown = 150
        self.image = self.animation_list[self.action][self.frame_index]
        if pygame.time.get_ticks() - self.update_time > animation_cooldown:
            self.update_time = pygame.time.get_ticks()
            self.frame_index += 1
        if self.frame_index >= len(self.animation_list[self.action]):
            self.frame_index = 0

    def draw(self):
        screen.blit(self.image, self.rect)

fridge = Fighter(200, 380, 'Fridge', 150, 40, "Ally")
#opp_fridge = Fighter(400, 380, "Fridge", 150, 40, "Opponent")

run = True
while run:
    clock.tick(fps)

    draw_bg()

    draw_panel()

    fridge.update()
    #opp_fridge.update()
    fridge.draw()
    #opp_fridge.draw()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            run = False
    pygame.display.update()

pygame.quit()