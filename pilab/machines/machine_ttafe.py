import random

class MachineTTAFE(object):
    def __init__(self):
        # Create main board with all blanks
        self.dim = 5
        self.data = {}
        self.data['board_n'] = [[0]*self.dim, [0]*self.dim, [0]*self.dim, [0]*self.dim, [0]*self.dim]
        self.data['board_t'] = {
            "0":{"0":None,"1":None,"2":None,"3":None,"4":None},
            "1":{"0":None,"1":None,"2":None,"3":None,"4":None},
            "2":{"0":None,"1":None,"2":None,"3":None,"4":None},
            "3":{"0":None,"1":None,"2":None,"3":None,"4":None},
            "4":{"0":None,"1":None,"2":None,"3":None,"4":None}
        }
        
        self.changed = True
        
        self.board = self.data['board_n']
        
        self.add_new_tile()
        self.add_new_tile()
                
    def shift(self, udlr):
        if udlr == "up":
            self.up()
        elif udlr == "down":
            self.down()
        elif udlr == "left":
            self.left()
        elif udlr == "right":
            self.right()
        
    def up(self):
        board = self.board
        dim = self.dim
        for x in range(dim): # x
            column = board[x]
            for y in range(1, dim): # y
                above = y-1
                current = y
                if column[current] != 0:
                    if column[above] == 0:
                        column[above] = column[current]
                        column[current] = 0
                        self.changed = True
                    elif column[above] == column[current]:
                        column[above] *= 2
                        column[current] = 0
                        self.changed = True
                    
    def down(self):
        board = self.board
        dim = self.dim
        for x in range(dim): # x
            column = board[x]
            for y in range(dim-2, -1, -1):
                below = y+1
                current = y
                if column[current] != 0:
                    if column[below] == 0:
                        column[below] = column[current]
                        column[current] = 0
                        self.changed = True
                    elif column[below] == column[current]:
                        column[below] *= 2
                        column[current] = 0
                        self.changed = True
                    
    def left(self):
        board = self.board
        dim = self.dim
        for y in range(dim): # x
            for x in range(1, dim): # y
                left = x-1
                current = x
                if board[current][y] != 0:
                    if board[left][y] == 0:
                        board[left][y] = board[current][y]
                        board[current][y] = 0
                        self.changed = True
                    elif board[left][y] == board[current][y]:
                        board[left][y] *= 2
                        board[current][y] = 0
                        self.changed = True
        
    def right(self):
        board = self.board
        dim = self.dim
        for y in range(dim): # x
            for x in range(dim-2, -1, -1):
                right = x+1
                current = x
                if board[current][y] != 0:
                    if board[right][y] == 0:
                        board[right][y] = board[current][y]
                        board[current][y] = 0
                        self.changed = True
                    elif board[right][y] == board[current][y]:
                        board[right][y] *= 2
                        board[current][y] = 0
                        self.changed = True

    def translate_board(self):
        bt = self.data['board_t']
        bn = self.data['board_n']
        for x in range(self.dim):
            for y in range(self.dim):
                bt[str(x)][str(y)] = str(bn[x][y])
                
    def add_new_tile(self):
        # Generate the value 1 or 2.4
        val = random.randrange(100,240)
        val /= 100
        # Scan the board for empty spaces and store them
        spaces = []
        for x in range(self.dim):
            for y in range(self.dim):
                if self.board[x][y] == 0:
                    spaces.append([x,y])
        # Pick a random space
        if spaces:
            picked = spaces[random.randrange(0, len(spaces))]
            self.board[picked[0]][picked[1]] = val
        else:
            pass # You lose

    def update(self):
        if self.changed:
            self.add_new_tile()
            self.translate_board()
            self.changed = False
