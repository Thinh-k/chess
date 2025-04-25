import asyncio
import platform
import pygame
import abc

WIDTH = 800
HEIGHT = 720
SQUARE_SIZE = 80
FPS = 60
BOARD_SIZE = 8
COLORS = {
    'dark_gray': (100, 100, 100),
    'light_gray': (200, 200, 200),
    'gray': (150, 150, 150),
    'gold': (255, 215, 0),
    'black': (0, 0, 0),
    'white': (255, 255, 255),
    'red': (255, 0, 0),
    'blue': (0, 0, 255),
    'dark_red': (139, 0, 0),
    'dark_blue': (0, 0, 139)
}

class Piece(abc.ABC):
    def __init__(self, color, position):
        self.color = color
        self.position = position
        self.has_moved = False
        self.image = None
        self.small_image = None

    @abc.abstractmethod
    def get_raw_valid_moves(self, game):
        pass

    @abc.abstractmethod
    def get_valid_moves(self, game):
        pass

    def load_image(self, name, size_large=(64, 64), size_small=(36, 36)):
        self.image = pygame.transform.scale(
            pygame.image.load(f'assets/images/{self.color}_{name}.png'), size_large)
        self.small_image = pygame.transform.scale(
            pygame.image.load(f'assets/images/{self.color}_{name}.png'), size_small)

class Pawn(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.load_image('pawn', size_large=(52, 52))
        
    def get_raw_valid_moves(self, game):
        moves = []
        x, y = self.position
        direction = 1 if self.color == 'white' else -1
        start_row = 1 if self.color == 'white' else 6
        
        one_step = (x, y + direction)
        if game.is_valid_square(one_step) and not game.is_occupied(one_step):
            moves.append(one_step)
            two_steps = (x, y + 2 * direction)
            if y == start_row and game.is_valid_square(two_steps) and not game.is_occupied(two_steps):
                moves.append(two_steps)
        
        for dx in [-1, 1]:
            capture = (x + dx, y + direction)
            if game.is_valid_square(capture) and game.is_enemy_piece(capture, self.color):
                moves.append(capture)
            ep = game.get_en_passant_target(self.color)
            if capture == ep:
                moves.append(capture)
        
        return moves, []

    def get_valid_moves(self, game):
        moves, castle_moves = self.get_raw_valid_moves(game)
        valid_moves = [move for move in moves if not game.would_expose_king(self, move)]
        return valid_moves, castle_moves

class Rook(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.load_image('rook')
        
    def get_raw_valid_moves(self, game):
        moves = self._get_linear_moves(game, [(0, 1), (0, -1), (1, 0), (-1, 0)])
        return moves, []
    
    def get_valid_moves(self, game):
        moves, castle_moves = self.get_raw_valid_moves(game)
        valid_moves = [move for move in moves if not game.would_expose_king(self, move)]
        return valid_moves, castle_moves
    
    def _get_linear_moves(self, game, directions):
        moves = []
        x, y = self.position
        for dx, dy in directions:
            for i in range(1, BOARD_SIZE):
                target = (x + i * dx, y + i * dy)
                if not game.is_valid_square(target):
                    break
                if game.is_occupied_by_friend(target, self.color):
                    break
                moves.append(target)
                if game.is_occupied_by_enemy(target, self.color):
                    break
        return moves

class Knight(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.load_image('knight')
        
    def get_raw_valid_moves(self, game):
        moves = []
        x, y = self.position
        targets = [(1, 2), (1, -2), (2, 1), (2, -1), (-1, 2), (-1, -2), (-2, 1), (-2, -1)]
        for dx, dy in targets:
            target = (x + dx, y + dy)
            if game.is_valid_square(target) and not game.is_occupied_by_friend(target, self.color):
                moves.append(target)
        return moves, []

    def get_valid_moves(self, game):
        moves, castle_moves = self.get_raw_valid_moves(game)
        valid_moves = [move for move in moves if not game.would_expose_king(self, move)]
        return valid_moves, castle_moves

class Bishop(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.load_image('bishop')
        
    def get_raw_valid_moves(self, game):
        moves = self._get_linear_moves(game, [(1, 1), (1, -1), (-1, 1), (-1, -1)])
        return moves, []
    
    def get_valid_moves(self, game):
        moves, castle_moves = self.get_raw_valid_moves(game)
        valid_moves = [move for move in moves if not game.would_expose_king(self, move)]
        return valid_moves, castle_moves
    
    def _get_linear_moves(self, game, directions):
        return Rook._get_linear_moves(self, game, directions)

class Queen(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.load_image('queen')
        
    def get_raw_valid_moves(self, game):
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]
        moves = Rook._get_linear_moves(self, game, directions)
        return moves, []

    def get_valid_moves(self, game):
        moves, castle_moves = self.get_raw_valid_moves(game)
        valid_moves = [move for move in moves if not game.would_expose_king(self, move)]
        return valid_moves, castle_moves

class King(Piece):
    def __init__(self, color, position):
        super().__init__(color, position)
        self.load_image('king')
        
    def get_raw_valid_moves(self, game):
        moves = []
        castle_moves = []
        x, y = self.position
        targets = [(1, 0), (1, 1), (1, -1), (-1, 0), (-1, 1), (-1, -1), (0, 1), (0, -1)]
        
        for dx, dy in targets:
            target = (x + dx, y + dy)
            if game.is_valid_square(target) and not game.is_occupied_by_friend(target, self.color):
                moves.append(target)
        
        if not self.has_moved and not game.is_in_check(self.color):
            for rook_pos in [(0, y), (7, y)]:
                rook = game.get_piece_at(rook_pos)
                if isinstance(rook, Rook) and rook.color == self.color and not rook.has_moved:
                    if rook_pos[0] > x:
                        squares = [(x + 1, y), (x + 2, y)]
                        final_king = (x + 2, y)
                        final_rook = (x + 1, y)
                    else:
                        squares = [(x - 1, y), (x - 2, y), (x - 3, y)]
                        final_king = (x - 2, y)
                        final_rook = (x - 1, y)
                    if all(not game.is_occupied(s) for s in squares[:2]) and \
                       all(not game.is_square_attacked(s, self.color) for s in squares[:2]):
                        castle_moves.append((final_king, final_rook))
        
        return moves, castle_moves

    def get_valid_moves(self, game):
        moves, castle_moves = self.get_raw_valid_moves(game)
        valid_moves = [move for move in moves if not game.would_expose_king(self, move)]
        return valid_moves, castle_moves

class Board:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.Font('freesansbold.ttf', 16)
        self.medium_font = pygame.font.Font('freesansbold.ttf', 32)
        self.big_font = pygame.font.Font('freesansbold.ttf', 40)
        
    def draw(self, game):
        self.screen.fill(COLORS['dark_gray'])
        self._draw_squares()
        self._draw_status(game)
        self._draw_pieces(game)
        self._draw_captured(game)
        self._draw_check(game)
        if game.selected_piece:
            self._draw_valid_moves(game)
            if isinstance(game.selected_piece, King):
                self._draw_castling(game)
        if game.white_promote or game.black_promote:
            self._draw_promotion(game)
        if game.winner:
            self._draw_game_over(game)
        
    def _draw_squares(self):
        for i in range(32):
            col = i % 4
            row = i // 4
            x = 480 - (col * 160) if row % 2 == 0 else 560 - (col * 160)
            pygame.draw.rect(self.screen, COLORS['light_gray'], [x, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE])
        pygame.draw.rect(self.screen, COLORS['gray'], [0, 640, WIDTH, SQUARE_SIZE])
        pygame.draw.rect(self.screen, COLORS['gold'], [0, 640, WIDTH, SQUARE_SIZE], 4)
        pygame.draw.rect(self.screen, COLORS['gold'], [640, 0, 160, HEIGHT], 4)
        for i in range(9):
            pygame.draw.line(self.screen, COLORS['black'], (0, SQUARE_SIZE * i), (640, SQUARE_SIZE * i), 2)
            pygame.draw.line(self.screen, COLORS['black'], (SQUARE_SIZE * i, 0), (SQUARE_SIZE * i, 640), 2)
        self.screen.blit(self.medium_font.render('BO CUOC', True, COLORS['black']), (648, 664))
        
    def _draw_status(self, game):
        status_text = ['Trang: Chon quan de di chuyen', 'Trang: Chon diem den',
                      'Den: Chon quan de di chuyen', 'Den: Chon diem den']
        self.screen.blit(self.big_font.render(status_text[game.turn_step], True, COLORS['black']), (16, 656))
        if game.white_promote or game.black_promote:
            pygame.draw.rect(self.screen, COLORS['gray'], [0, 640, WIDTH - 160, SQUARE_SIZE])
            pygame.draw.rect(self.screen, COLORS['gold'], [0, 640, WIDTH - 160, SQUARE_SIZE], 4)
            self.screen.blit(self.big_font.render('Chon quan de phong cap Tot', True, COLORS['black']), (16, 656))
            
    def _draw_pieces(self, game):
        for piece in game.pieces:
            x, y = piece.position
            offset = (18, 24) if isinstance(piece, Pawn) else (8, 8)
            self.screen.blit(piece.image, (x * SQUARE_SIZE + offset[0], y * SQUARE_SIZE + offset[1]))
            if piece == game.selected_piece:
                color = COLORS['red'] if piece.color == 'white' else COLORS['blue']
                pygame.draw.rect(self.screen, color, [x * SQUARE_SIZE + 1, y * SQUARE_SIZE + 1, SQUARE_SIZE, SQUARE_SIZE], 2)
                
    def _draw_captured(self, game):
        piece_types = ['pawn', 'queen', 'king', 'knight', 'rook', 'bishop']
        for i, piece_type in enumerate(game.captured_pieces['white']):
            if piece_type in piece_types:
                index = piece_types.index(piece_type)
                self.screen.blit(game.white_small_images[index], (660, 8 + 48 * i))
        for i, piece_type in enumerate(game.captured_pieces['black']):
            if piece_type in piece_types:
                index = piece_types.index(piece_type)
                self.screen.blit(game.black_small_images[index], (740, 8 + 48 * i))
            
    def _draw_check(self, game):
        if game.counter >= 30:
            game.counter = 0
        if game.is_in_check('white') and game.turn_step < 2:
            king = game.get_king('white')
            if king and game.counter < 15:
                pygame.draw.rect(self.screen, COLORS['dark_red'], [king.position[0] * SQUARE_SIZE + 1,
                                                                  king.position[1] * SQUARE_SIZE + 1, SQUARE_SIZE, SQUARE_SIZE], 4)
        elif game.is_in_check('black') and game.turn_step >= 2:
            king = game.get_king('black')
            if king and game.counter < 15:
                pygame.draw.rect(self.screen, COLORS['dark_blue'], [king.position[0] * SQUARE_SIZE + 1,
                                                                   king.position[1] * SQUARE_SIZE + 1, SQUARE_SIZE, SQUARE_SIZE], 4)
                
    def _draw_valid_moves(self, game):
        color = COLORS['red'] if game.turn_step < 2 else COLORS['blue']
        for move in game.valid_moves:
            pygame.draw.circle(self.screen, color, (move[0] * SQUARE_SIZE + 40, move[1] * SQUARE_SIZE + 40), 4)
            
    def _draw_castling(self, game):
        color = COLORS['red'] if game.turn_step < 2 else COLORS['blue']
        for king_pos, rook_pos in game.castle_moves:
            pygame.draw.circle(self.screen, color, (king_pos[0] * SQUARE_SIZE + 40, king_pos[1] * SQUARE_SIZE + 56), 6)
            self.screen.blit(self.font.render('vua', True, COLORS['black']),
                            (king_pos[0] * SQUARE_SIZE + 24, king_pos[1] * SQUARE_SIZE + 56))
            pygame.draw.circle(self.screen, color, (rook_pos[0] * SQUARE_SIZE + 40, rook_pos[1] * SQUARE_SIZE + 56), 6)
            self.screen.blit(self.font.render('xe', True, COLORS['black']),
                            (rook_pos[0] * SQUARE_SIZE + 24, rook_pos[1] * SQUARE_SIZE + 56))
            pygame.draw.line(self.screen, color,
                            (king_pos[0] * SQUARE_SIZE + 40, king_pos[1] * SQUARE_SIZE + 56),
                            (rook_pos[0] * SQUARE_SIZE + 40, rook_pos[1] * SQUARE_SIZE + 56), 2)
            
    def _draw_promotion(self, game):
        pygame.draw.rect(self.screen, COLORS['dark_gray'], [640, 0, 160, 336])
        promotions = game.white_promotions if game.white_promote else game.black_promotions
        images = game.white_images if game.white_promote else game.black_images
        color = COLORS['white'] if game.white_promote else COLORS['black']
        for i, piece in enumerate(promotions):
            index = ['pawn', 'queen', 'king', 'knight', 'rook', 'bishop'].index(piece)
            self.screen.blit(images[index], (688, 4 + 80 * i))
        pygame.draw.rect(self.screen, color, [640, 0, 160, 336], 6)
        
    def _draw_game_over(self, game):
        pygame.draw.rect(self.screen, COLORS['black'], [160, 160, 320, 56])
        winner_text = 'Hoa' if game.winner == 'Hoa' else f'{game.winner} thang'
        self.screen.blit(self.font.render(winner_text, True, COLORS['white']), (168, 168))
        self.screen.blit(self.font.render('Nhan ENTER de choi lai', True, COLORS['white']), (168, 192))

class ChessGame:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode([WIDTH, HEIGHT])
        pygame.display.set_caption('Co Vua Hai Nguoi Pygame')
        self.clock = pygame.time.Clock()
        self.board = Board(self.screen)
        self.reset()
        
    def reset(self):
        self.pieces = []
        self.captured_pieces = {'white': [], 'black': []}
        self.white_images = []
        self.black_images = []
        self.white_small_images = []
        self.black_small_images = []
        self.white_promotions = ['queen', 'rook', 'bishop', 'knight']
        self.black_promotions = ['queen', 'rook', 'bishop', 'knight']
        self.turn_step = 0
        self.selected_piece = None
        self.valid_moves = []
        self.castle_moves = []
        self.winner = ''
        self.game_over = False
        self.white_ep = (100, 100)
        self.black_ep = (100, 100)
        self.white_promote = False
        self.black_promote = False
        self.promo_index = None
        self.counter = 0
        
        piece_order = ['rook', 'knight', 'bishop', 'queen', 'king', 'bishop', 'knight', 'rook']
        for i in range(8):
            self.pieces.append(Pawn('white', (i, 1)))
            self.pieces.append(Pawn('black', (i, 6)))
            piece_class = {'rook': Rook, 'knight': Knight, 'bishop': Bishop, 'queen': Queen, 'king': King}[piece_order[i]]
            self.pieces.append(piece_class('white', (i, 0)))
            self.pieces.append(piece_class('black', (i, 7)))
        
        white_king = self.get_king('white')
        black_king = self.get_king('black')
        if not white_king or not black_king:
            raise RuntimeError("Khong the khoi tao vua trong reset")
        
        for piece_type in ['pawn', 'queen', 'king', 'knight', 'rook', 'bishop']:
            piece = next(p for p in self.pieces if p.color == 'white' and piece_type in str(type(p)).lower())
            self.white_images.append(piece.image)
            self.white_small_images.append(piece.small_image)
            piece = next(p for p in self.pieces if p.color == 'black' and piece_type in str(type(p)).lower())
            self.black_images.append(piece.image)
            self.black_small_images.append(piece.small_image)
            
    def is_valid_square(self, pos):
        x, y = pos
        return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE
    
    def is_occupied(self, pos):
        return any(p.position == pos for p in self.pieces)
    
    def is_occupied_by_friend(self, pos, color):
        return any(p.position == pos and p.color == color for p in self.pieces)
    
    def is_occupied_by_enemy(self, pos, color):
        return any(p.position == pos and p.color != color for p in self.pieces)
    
    def is_enemy_piece(self, pos, color):
        return self.is_occupied_by_enemy(pos, color)
    
    def get_piece_at(self, pos):
        for piece in self.pieces:
            if piece.position == pos:
                return piece
        return None
    
    def get_king(self, color):
        for piece in self.pieces:
            if isinstance(piece, King) and piece.color == color:
                return piece
        return None
    
    def get_en_passant_target(self, color):
        return self.black_ep if color == 'white' else self.white_ep
    
    def is_in_check(self, color):
        king = self.get_king(color)
        if not king:
            return False
        enemy_pieces = [p for p in self.pieces if p.color != color and not isinstance(p, King)]
        for piece in enemy_pieces:
            moves, _ = piece.get_raw_valid_moves(self)
            if king.position in moves:
                return True
        return False
    
    def is_square_attacked(self, pos, color):
        enemy_pieces = [p for p in self.pieces if p.color != color and not isinstance(p, King)]
        for piece in enemy_pieces:
            moves, _ = piece.get_raw_valid_moves(self)
            if pos in moves:
                return True
        return False
    
    def would_expose_king(self, piece, new_pos):
        original_pos = piece.position
        captured = self.get_piece_at(new_pos)
        piece.position = new_pos
        if captured and captured != piece:
            self.pieces.remove(captured)
        
        in_check = self.is_in_check(piece.color)
        
        piece.position = original_pos
        if captured and captured != piece:
            self.pieces.append(captured)
        
        return in_check
    
    def is_checkmate_or_stalemate(self, color):
        if not self.is_in_check(color):
            for piece in self.pieces:
                if piece.color == color:
                    moves, castle_moves = piece.get_valid_moves(self)
                    if moves or castle_moves:
                        return False, False
            return True, False
        else:
            for piece in self.pieces:
                if piece.color == color:
                    moves, castle_moves = piece.get_valid_moves(self)
                    if moves or castle_moves:
                        return False, False
            return False, True
        return False, False
    
    def check_promotion(self):
        self.white_promote = False
        self.black_promote = False
        self.promo_index = None
        for piece in self.pieces:
            if isinstance(piece, Pawn):
                if piece.color == 'white' and piece.position[1] == 7:
                    self.white_promote = True
                    self.promo_index = piece
                elif piece.color == 'black' and piece.position[1] == 0:
                    self.black_promote = True
                    self.promo_index = piece
        return self.white_promote, self.black_promote, self.promo_index
    
    def handle_promotion_selection(self, pos):
        x, y = pos
        if (self.white_promote or self.black_promote) and x > 7 and y < 4:
            promotions = self.white_promotions if self.white_promote else self.black_promotions
            piece_class = {'queen': Queen, 'rook': Rook, 'bishop': Bishop, 'knight': Knight}[promotions[y]]
            new_piece = piece_class(self.promo_index.color, self.promo_index.position)
            self.pieces.remove(self.promo_index)
            self.pieces.append(new_piece)
            self.white_promote = False
            self.black_promote = False
            self.promo_index = None
    
    def check_en_passant(self, piece, old_pos, new_pos):
        if isinstance(piece, Pawn) and abs(old_pos[1] - new_pos[1]) == 2:
            return (new_pos[0], (old_pos[1] + new_pos[1]) // 2)
        return (100, 100)
    
    def handle_move(self, piece, new_pos):
        old_pos = piece.position
        captured = self.get_piece_at(new_pos)
        piece.position = new_pos
        piece.has_moved = True
        
        if captured and captured.color != piece.color:
            if isinstance(captured, King):
                return
            piece_type_map = {
                Pawn: 'pawn',
                Queen: 'queen',
                King: 'king',
                Knight: 'knight',
                Rook: 'rook',
                Bishop: 'bishop'
            }
            piece_type = piece_type_map.get(type(captured), '')
            if piece_type:
                self.captured_pieces[captured.color].append(piece_type)
                self.pieces.remove(captured)
        
        ep_target = self.black_ep if piece.color == 'white' else self.white_ep
        if new_pos == ep_target and isinstance(piece, Pawn):
            captured_pos = (ep_target[0], ep_target[1] - 1 if piece.color == 'white' else ep_target[1] + 1)
            captured = self.get_piece_at(captured_pos)
            if captured:
                self.captured_pieces[captured.color].append('pawn')
                self.pieces.remove(captured)
        
        if piece.color == 'white':
            self.white_ep = self.check_en_passant(piece, old_pos, new_pos)
            self.black_ep = (100, 100)
        else:
            self.black_ep = self.check_en_passant(piece, old_pos, new_pos)
            self.white_ep = (100, 100)
    
    def handle_castling(self, king, new_pos):
        if king.position[0] > new_pos[0]:
            rook_pos = (0, king.position[1])
            new_rook_pos = (new_pos[0] + 1, new_pos[1])
        else:
            rook_pos = (7, king.position[1])
            new_rook_pos = (new_pos[0] - 1, new_pos[1])
        rook = self.get_piece_at(rook_pos)
        if rook:
            king.position = new_pos
            king.has_moved = True
            rook.position = new_rook_pos
            rook.has_moved = True
    
    def handle_click(self, pos):
        if self.game_over:
            return
        x, y = pos[0] // SQUARE_SIZE, pos[1] // SQUARE_SIZE
        click_pos = (x, y)
        
        if click_pos in [(8, 8), (9, 8)]:
            self.winner = 'black' if self.turn_step < 2 else 'white'
            return
        
        if self.white_promote or self.black_promote:
            self.handle_promotion_selection(click_pos)
            return
        
        if self.turn_step <= 1:
            if self.is_valid_square(click_pos) and self.get_piece_at(click_pos) and self.get_piece_at(click_pos).color == 'white':
                self.selected_piece = self.get_piece_at(click_pos)
                self.valid_moves, self.castle_moves = self.selected_piece.get_valid_moves(self)
                self.turn_step = 1
            elif click_pos in self.valid_moves and self.selected_piece:
                self.handle_move(self.selected_piece, click_pos)
                self.turn_step = 2
                self.selected_piece = None
                self.valid_moves = []
                self.castle_moves = []
            elif self.selected_piece and isinstance(self.selected_piece, King):
                for king_pos, _ in self.castle_moves:
                    if click_pos == king_pos:
                        self.handle_castling(self.selected_piece, click_pos)
                        self.turn_step = 2
                        self.selected_piece = None
                        self.valid_moves = []
                        self.castle_moves = []
                        break
        else:
            if self.is_valid_square(click_pos) and self.get_piece_at(click_pos) and self.get_piece_at(click_pos).color == 'black':
                self.selected_piece = self.get_piece_at(click_pos)
                self.valid_moves, self.castle_moves = self.selected_piece.get_valid_moves(self)
                self.turn_step = 3
            elif click_pos in self.valid_moves and self.selected_piece:
                self.handle_move(self.selected_piece, click_pos)
                self.turn_step = 0
                self.selected_piece = None
                self.valid_moves = []
                self.castle_moves = []
            elif self.selected_piece and isinstance(self.selected_piece, King):
                for king_pos, _ in self.castle_moves:
                    if click_pos == king_pos:
                        self.handle_castling(self.selected_piece, click_pos)
                        self.turn_step = 0
                        self.selected_piece = None
                        self.valid_moves = []
                        self.castle_moves = []
                        break
        
        current_color = 'black' if self.turn_step < 2 else 'white'
        is_stalemate, is_checkmate = self.is_checkmate_or_stalemate(current_color)
        if is_checkmate:
            self.winner = 'white' if current_color == 'black' else 'black'
            self.game_over = True
        elif is_stalemate:
            self.winner = 'Hoa'
            self.game_over = True
    
    def handle_keydown(self, key):
        if self.game_over and key == pygame.K_RETURN:
            self.reset()
    
    def setup(self):
        self.reset()
        
    async def update_loop(self):
        try:
            self.clock.tick(FPS)
            self.counter += 1
            self.check_promotion()
            if self.winner:
                self.game_over = True
            self.board.draw(self)
            pygame.display.flip()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
                if event.type == pygame.KEYDOWN:
                    self.handle_keydown(event.key)
        except Exception as e:
            print(f"Loi trong update_loop: {e}")
            raise
    
async def main():
    game = ChessGame()
    game.setup()
    while True:
        await game.update_loop()
        await asyncio.sleep(1.0 / FPS)

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())