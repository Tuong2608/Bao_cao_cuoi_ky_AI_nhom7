import pygame
import random
from collections import deque, Counter
import time
import heapq
import math
import sys
import os
import itertools

# --- CONSTANTS ---
WIDTH, HEIGHT = 1280, 900
TUBES_PER_ROW = 5
TUBE_WIDTH, TUBE_HEIGHT = 80, 300
TUBE_SPACING = 20
CAPACITY = 4
FPS = 60
AUTO_PLAY_DELAY = 0.3

# Animation Constants
LIFT_HEIGHT = 30
LIFT_SPEED = 5

# Colors
ALL_COLORS = [
    (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
    (255, 165, 0), (128, 0, 128), (0, 255, 255), (255, 192, 203),
    (165, 42, 42), (128, 128, 0), (0, 128, 0), (255, 0, 255)
]

# UI Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY = (128, 128, 128)
GREEN = (40, 180, 99)
BLUE_HIGHLIGHT = (52, 152, 219)
PANEL_BG = (240, 240, 240, 220)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)

# Initialize Pygame
pygame.init()
pygame.font.init()
try:
    pygame.mixer.init()
except Exception:
    pass

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Water Sort Puzzle")

# Assets Loader
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Load fonts/images/sounds
TUBE_IMG = None
BG_IMG = None
SOUND_SELECT = None
SOUND_WIN = None
SOUND_CLICK = None
FONT_S = None
FONT_M = None
FONT_L = None

try:
    FONT_PATH = resource_path('assets/fonts/FredokaOne-Regular.ttf')
    FONT_S = pygame.font.Font(FONT_PATH, 18)
    FONT_M = pygame.font.Font(FONT_PATH, 26)
    FONT_L = pygame.font.Font(FONT_PATH, 48)
except Exception:
    FONT_S = pygame.font.SysFont('arial', 18)
    FONT_M = pygame.font.SysFont('arial', 26)
    FONT_L = pygame.font.SysFont('arial', 48)

try:
    TUBE_IMG = pygame.image.load(resource_path('assets/images/tube.png')).convert_alpha()
    TUBE_IMG = pygame.transform.scale(TUBE_IMG, (TUBE_WIDTH + 20, TUBE_HEIGHT + 20))
except Exception:
    TUBE_IMG = None

try:
    BG_IMG = pygame.image.load(resource_path('assets/images/background.png')).convert()
    BG_IMG = pygame.transform.scale(BG_IMG, (WIDTH, HEIGHT))
except Exception:
    BG_IMG = None

try:
    SOUND_SELECT = pygame.mixer.Sound(resource_path('assets/sounds/select.ogg'))
    SOUND_WIN = pygame.mixer.Sound(resource_path('assets/sounds/win.ogg'))
    SOUND_CLICK = pygame.mixer.Sound(resource_path('assets/sounds/click.ogg'))
except Exception:
    SOUND_SELECT = SOUND_WIN = SOUND_CLICK = None

# --- Tube Class ---
class Tube:
    def __init__(self, x, y, colors, is_hidden_mode=False, is_blind_mode=False):
        self.x = x
        self.y = y
        self.original_y = y
        self.current_y = y
        self.capacity = CAPACITY
        self.segments = []
        self.is_blind_mode = is_blind_mode
        self.is_hidden_mode = is_hidden_mode

        for i, color in enumerate(colors):
            is_visible = True
            if is_blind_mode:
                is_visible = False
            elif is_hidden_mode:
                is_visible = (i == len(colors) - 1)
            self.segments.append([color, is_visible])

        self.image_width = TUBE_WIDTH + 20
        self.image_height = TUBE_HEIGHT + 20
        self.INNER_X_OFFSET = 18
        self.INNER_TOP_OFFSET = 28
        self.INNER_BOTTOM_OFFSET = 20
        usable_height = self.image_height - (self.INNER_TOP_OFFSET + self.INNER_BOTTOM_OFFSET)
        self.WATER_HEIGHT = usable_height // self.capacity
        self.rect = pygame.Rect(self.x, self.y, self.image_width, self.image_height)
        self.is_selected = False
        self.colors = [seg[0] for seg in self.segments]

    def update(self):
        if self.is_selected and self.current_y > self.original_y - LIFT_HEIGHT:
            self.current_y -= LIFT_SPEED
        elif not self.is_selected and self.current_y < self.original_y:
            self.current_y += LIFT_SPEED
        self.rect.y = self.current_y

    def draw(self, screen):
        if TUBE_IMG:
            screen.blit(TUBE_IMG, (self.x, self.current_y))
        else:
            pygame.draw.rect(screen, (180, 180, 180), (self.x, self.current_y, self.image_width, self.image_height),
                             border_radius=8)

        water_x = self.x + self.INNER_X_OFFSET
        water_width = self.image_width - (self.INNER_X_OFFSET * 2)
        for i, (color, is_visible) in enumerate(self.segments):
            draw_color = color if is_visible else GREY
            water_y = (self.current_y + self.image_height - self.INNER_BOTTOM_OFFSET) - (i + 1) * self.WATER_HEIGHT
            pygame.draw.rect(screen, draw_color, (water_x, water_y, water_width, self.WATER_HEIGHT), border_radius=4)
            if not is_visible:
                q_mark_surf = FONT_M.render('?', True, WHITE)
                segment_rect = pygame.Rect(water_x, water_y, water_width, self.WATER_HEIGHT)
                q_mark_rect = q_mark_surf.get_rect(center=segment_rect.center)
                screen.blit(q_mark_surf, q_mark_rect)

    def can_pour(self, other):
        if not self.segments:
            return False
        if len(other.segments) >= other.capacity:
            return False
        top_color, _ = self.segments[-1]
        return not other.segments or other.segments[-1][0] == top_color

    def pour(self, other):
        if self.can_pour(other):
            segment_to_move = self.segments.pop()
            other.segments.append(segment_to_move)
            if self.segments and not self.is_blind_mode:
                self.segments[-1][1] = True
            self.colors = [seg[0] for seg in self.segments]
            other.colors = [seg[0] for seg in other.segments]
            return True
        return False

    def get_pourable_amount(self, other):
        if not self.can_pour(other): return 0
        top_color, _ = self.segments[-1]
        count = 0
        for i in range(len(self.segments) - 1, -1, -1):
            if self.segments[i][0] == top_color:
                count += 1
            else:
                break
        space = other.capacity - len(other.segments)
        return min(count, space)

    def transfer_to(self, other, amount):
        moved = 0
        if amount <= 0 or not self.segments: return 0
        top_color = self.segments[-1][0]
        while moved < amount and self.segments and len(other.segments) < other.capacity:
            if self.segments[-1][0] != top_color: break
            segment = self.segments.pop()
            other.segments.append(segment)
            moved += 1
        if self.segments and not self.is_blind_mode:
            self.segments[-1][1] = True
        self.colors = [seg[0] for seg in self.segments]
        other.colors = [seg[0] for seg in other.segments]
        return moved

# --- Core Solver Helpers ---
def can_pour_on_state(state, from_idx, to_idx):
    if from_idx == to_idx: return False
    source_tube, dest_tube = state[from_idx], state[to_idx]
    if not source_tube: return False
    if len(dest_tube) >= CAPACITY: return False
    return not dest_tube or dest_tube[-1] == source_tube[-1]

def apply_move_on_state(state, from_idx, to_idx):
    state_list = [list(tube) for tube in state]
    if not state_list[from_idx]: return state

    color_to_move = state_list[from_idx].pop()
    state_list[to_idx].append(color_to_move)

    return tuple(tuple(tube) for tube in state_list)

def get_all_valid_moves(state):
    moves = []
    n = len(state)
    for i in range(n):
        for j in range(n):
            if can_pour_on_state(state, i, j):
                moves.append((i, j))
    return moves

def heuristic(state):
    total_score = 0
    for tube in state:
        if not tube: continue
        if len(set(tube)) <= 1:
            continue
        try:
            counts = Counter(tube)
            most_common_color = counts.most_common(1)[0][0]
            for color in tube:
                if color != most_common_color:
                    total_score += 1
        except IndexError:
            continue
    return total_score

# --- All Solvers ---
def solve_bfs(initial_tubes):
    start_time = time.time()
    initial_state = tuple(tuple(t.colors) for t in initial_tubes)
    queue = deque([(initial_state, [])])
    visited = {initial_state}
    nodes = 0
    num_tubes = len(initial_tubes)

    while queue:
        state, moves = queue.popleft()
        nodes += 1
        if all(len(set(colors)) <= 1 and (len(colors) == 0 or len(colors) == 4) for colors in state):
            return {'path': moves, 'steps': len(moves), 'time': time.time() - start_time, 'nodes': nodes}
        for i in range(num_tubes):
            for j in range(num_tubes):
                if can_pour_on_state(state, i, j):
                    new_state = apply_move_on_state(state, i, j)
                    if new_state not in visited:
                        visited.add(new_state)
                        queue.append((new_state, moves + [(i, j)]))
    return None

def solve_dfs(initial_tubes):
    start_time = time.time()
    initial_state = tuple(tuple(t.colors) for t in initial_tubes)
    stack = [(initial_state, [])]
    visited = {initial_state}
    nodes = 0
    num_tubes = len(initial_tubes)

    while stack:
        state, moves = stack.pop()
        nodes += 1
        if all(len(set(colors)) <= 1 and (len(colors) == 0 or len(colors) == 4) for colors in state):
            return {'path': moves, 'steps': len(moves), 'time': time.time() - start_time, 'nodes': nodes}
        valid_moves = get_all_valid_moves(state)
        random.shuffle(valid_moves)
        for move in valid_moves:
            i, j = move
            new_state = apply_move_on_state(state, i, j)
            if new_state not in visited:
                visited.add(new_state)
                stack.append((new_state, moves + [(i, j)]))
    return None

def solve_a_star(initial_tubes):
    start_time = time.time()
    initial_state = tuple(tuple(t.colors) for t in initial_tubes)
    priority_queue = [(heuristic(initial_state), 0, initial_state, [])]
    visited = {initial_state: 0}
    nodes = 0
    num_tubes = len(initial_tubes)

    while priority_queue:
        f, g, state, moves = heapq.heappop(priority_queue)
        nodes += 1
        if all(len(set(colors)) <= 1 and (len(colors) == 0 or len(colors) == 4) for colors in state):
            return {'path': moves, 'steps': len(moves), 'time': time.time() - start_time, 'nodes': nodes}
        if g > visited[state]:
            continue
        for i in range(num_tubes):
            for j in range(num_tubes):
                if can_pour_on_state(state, i, j):
                    new_state = apply_move_on_state(state, i, j)
                    new_g = g + 1
                    if new_state not in visited or new_g < visited[new_state]:
                        visited[new_state] = new_g
                        new_f = new_g + heuristic(new_state)
                        heapq.heappush(priority_queue, (new_f, new_g, new_state, moves + [(i, j)]))
    return None

def solve_greedy(initial_tubes):
    start_time = time.time()
    initial_state = tuple(tuple(t.colors) for t in initial_tubes)
    priority_queue = [(heuristic(initial_state), initial_state, [])]
    visited = {initial_state}
    nodes = 0
    num_tubes = len(initial_tubes)

    while priority_queue:
        h, state, moves = heapq.heappop(priority_queue)
        nodes += 1
        if all(len(set(colors)) <= 1 and (len(colors) == 0 or len(colors) == 4) for colors in state):
            return {'path': moves, 'steps': len(moves), 'time': time.time() - start_time, 'nodes': nodes}
        for i in range(num_tubes):
            for j in range(num_tubes):
                if can_pour_on_state(state, i, j):
                    new_state = apply_move_on_state(state, i, j)
                    if new_state not in visited:
                        visited.add(new_state)
                        new_h = heuristic(new_state)
                        heapq.heappush(priority_queue, (new_h, new_state, moves + [(i, j)]))
    return None

def solve_sa(initial_tubes):
    start_time = time.time()
    initial_state = tuple(tuple(t.colors) for t in initial_tubes)
    current_state = initial_state
    current_path = []
    T = 1.0
    cooling_rate = 0.995
    max_iter = 10000
    nodes = 0

    for iter in range(max_iter):
        nodes += 1
        if all(len(set(colors)) <= 1 and (len(colors) == 0 or len(colors) == 4) for colors in current_state):
            return {'path': current_path, 'steps': len(current_path), 'time': time.time() - start_time, 'nodes': nodes}
        valid_moves = get_all_valid_moves(current_state)
        if not valid_moves:
            current_state = initial_state
            current_path = []
            T = 1.0
            continue
        move = random.choice(valid_moves)
        new_state = apply_move_on_state(current_state, move[0], move[1])
        delta = heuristic(new_state) - heuristic(current_state)
        if delta < 0 or random.random() < math.exp(-delta / T):
            current_state = new_state
            current_path.append(move)
        T *= cooling_rate
        if T < 0.001:
            T = 1.0
            current_state = initial_state
            current_path = []
    return None

def solve_hill_climb_restarts(initial_tubes):
    start_time = time.time()
    initial_state = tuple(tuple(t.colors) for t in initial_tubes)
    nodes = 0
    max_restarts = 10
    max_iterations_per_run = 100
    best_path_so_far = []
    lowest_heuristic_achieved = float('inf')

    for i in range(max_restarts):
        current_state = initial_state
        current_path = []
        for _ in range(max_iterations_per_run):
            nodes += 1
            if all(len(set(colors)) <= 1 and (len(colors) == 0 or len(colors) == 4) for colors in current_state):
                return {
                    'path': current_path,
                    'steps': len(current_path),
                    'time': time.time() - start_time,
                    'nodes': nodes,
                    'stuck': False
                }
            best_next_state = None
            best_move = None
            current_heuristic_val = heuristic(current_state)
            best_heuristic_val = current_heuristic_val
            for move in get_all_valid_moves(current_state):
                new_state = apply_move_on_state(current_state, move[0], move[1])
                new_heuristic = heuristic(new_state)
                if new_heuristic < best_heuristic_val:
                    best_heuristic_val = new_heuristic
                    best_next_state = new_state
                    best_move = move
            if best_move is not None:
                current_state = best_next_state
                current_path.append(best_move)
            else:
                break
        final_heuristic = heuristic(current_state)
        if final_heuristic < lowest_heuristic_achieved:
            lowest_heuristic_achieved = final_heuristic
            best_path_so_far = current_path
    if not best_path_so_far:
        return None
    return {
        'path': best_path_so_far,
        'steps': len(best_path_so_far),
        'time': time.time() - start_time,
        'nodes': nodes,
        'stuck': True
    }

def solve_backtracking(initial_tubes):
    start_time = time.time()
    initial_state = tuple(tuple(t.colors) for t in initial_tubes)
    nodes_visited = [0]
    path_visited = set()

    def is_goal(state):
        return all(len(set(colors)) <= 1 and (len(colors) == 0 or len(colors) == 4) for colors in state)

    def backtrack_recursive(state, path):
        nodes_visited[0] += 1
        if is_goal(state):
            return path
        if state in path_visited:
            return None
        path_visited.add(state)
        for move in get_all_valid_moves(state):
            new_state = apply_move_on_state(state, move[0], move[1])
            result = backtrack_recursive(new_state, path + [move])
            if result is not None:
                return result
        path_visited.remove(state)
        return None

    solution_path = backtrack_recursive(initial_state, [])
    if solution_path:
        return {
            'path': solution_path,
            'steps': len(solution_path),
            'time': time.time() - start_time,
            'nodes': nodes_visited[0]
        }
    return None

def solve_abca(initial_tubes):
    start_time = time.time()
    initial_state = tuple(tuple(t.colors) for t in initial_tubes)
    n_tubes = len(initial_tubes)
    NUM_BEES = 50
    MAX_CYCLES = 200
    LIMIT = 10
    MIN_PATH_LEN = 10
    MAX_PATH_LEN = 40
    nodes = 0

    def is_goal(state):
        return all(len(colors) == 0 or (len(colors) == 4 and len(set(colors)) == 1) for colors in state)

    def apply_path(state, path):
        current_state = state
        valid_path = []
        for move in path:
            from_t, to_t = move
            if can_pour_on_state(current_state, from_t, to_t):
                current_state = apply_move_on_state(current_state, from_t, to_t)
                valid_path.append(move)
                if is_goal(current_state):
                    break
        return current_state, valid_path

    def calculate_fitness(path):
        final_state, valid_path = apply_path(initial_state, path)
        if is_goal(final_state):
            return 10000 - len(valid_path)
        h_score = heuristic(final_state)
        return -h_score - len(path) * 0.1

    def generate_random_path():
        path_len = random.randint(MIN_PATH_LEN, MAX_PATH_LEN)
        path = []
        state = initial_state
        for _ in range(path_len):
            moves = get_all_valid_moves(state)
            if not moves: break
            move = random.choice(moves)
            path.append(move)
            state = apply_move_on_state(state, move[0], move[1])
        return path

    def generate_neighbor_path(path):
        new_path = path[:]
        if not new_path: return generate_random_path()
        mutation_type = random.random()
        if mutation_type < 0.5:
            idx = random.randint(0, len(new_path) - 1)
            new_path[idx] = (random.randint(0, n_tubes - 1), random.randint(0, n_tubes - 1))
        elif mutation_type < 0.75 and len(new_path) > MIN_PATH_LEN:
            new_path.pop(random.randint(0, len(new_path) - 1))
        else:
            idx = random.randint(0, len(new_path))
            new_path.insert(idx, (random.randint(0, n_tubes - 1), random.randint(0, n_tubes - 1)))
        return new_path[:MAX_PATH_LEN]

    food_sources = [generate_random_path() for _ in range(NUM_BEES)]
    fitness_scores = [calculate_fitness(p) for p in food_sources]
    trials = [0] * NUM_BEES
    best_solution_path = None
    best_fitness = -float('inf')

    for cycle in range(MAX_CYCLES):
        nodes += NUM_BEES * 2
        for i in range(NUM_BEES):
            new_path = generate_neighbor_path(food_sources[i])
            new_fitness = calculate_fitness(new_path)
            if new_fitness > fitness_scores[i]:
                food_sources[i] = new_path
                fitness_scores[i] = new_fitness
                trials[i] = 0
            else:
                trials[i] += 1
        total_fitness = sum(f for f in fitness_scores if f > 0)
        if total_fitness > 0:
            probabilities = [f / total_fitness for f in fitness_scores]
            for i in range(NUM_BEES):
                chosen_index = -1
                r = random.random()
                cumulative_prob = 0
                for j in range(NUM_BEES):
                    cumulative_prob += probabilities[j]
                    if r <= cumulative_prob:
                        chosen_index = j
                        break
                if chosen_index == -1: chosen_index = NUM_BEES - 1
                new_path = generate_neighbor_path(food_sources[chosen_index])
                new_fitness = calculate_fitness(new_path)
                if new_fitness > fitness_scores[chosen_index]:
                    food_sources[chosen_index] = new_path
                    fitness_scores[chosen_index] = new_fitness
                    trials[chosen_index] = 0
                else:
                    trials[chosen_index] += 1
        for i in range(NUM_BEES):
            if fitness_scores[i] > best_fitness:
                best_fitness = fitness_scores[i]
                best_solution_path = food_sources[i]
        if best_fitness > 9000:
            final_state, valid_path = apply_path(initial_state, best_solution_path)
            if is_goal(final_state):
                return {
                    'path': valid_path, 'steps': len(valid_path),
                    'time': time.time() - start_time, 'nodes': nodes
                }
        for i in range(NUM_BEES):
            if trials[i] > LIMIT:
                food_sources[i] = generate_random_path()
                fitness_scores[i] = calculate_fitness(food_sources[i])
                trials[i] = 0
    return None

# --- Blind Mode ---
def generate_blind_worlds(num_tubes, num_colors, num_empty=2):
    color_pool = []
    colors_list = ALL_COLORS[:num_colors]
    for color in colors_list:
        color_pool.extend([color] * 4)
    worlds = []
    max_worlds = 50
    for _ in range(max_worlds):
        random.shuffle(color_pool)
        world = []
        idx = 0
        for tube_idx in range(num_tubes):
            if tube_idx < num_colors:
                tube = tuple(color_pool[idx:idx + 4])
                idx += 4
            else:
                tube = ()
            world.append(tube)
        worlds.append(tuple(world))
    worlds = list(set(worlds))
    print(f"Generated {len(worlds)} possible worlds for blind mode")
    return worlds

def simulate_test_on_world(test, world):
    from_idx, to_idx = test
    source_tube = world[from_idx]
    dest_tube = world[to_idx]
    if not source_tube:
        return "failure"
    if len(dest_tube) >= 4:
        return "failure"
    if not dest_tube:
        return "success"
    if source_tube[-1] == dest_tube[-1]:
        return "success"
    return "failure"

def calculate_test_score(test, possible_worlds):
    from_idx, to_idx = test
    success_count = 0
    failure_count = 0
    for world in possible_worlds:
        result = simulate_test_on_world(test, world)
        if result == "success":
            success_count += 1
        else:
            failure_count += 1
    return min(success_count, failure_count)

def select_best_test(possible_worlds, tubes):
    candidate_tests = []
    for i in range(len(tubes)):
        if not tubes[i].segments:
            continue
        for j in range(len(tubes)):
            if i == j:
                continue
            candidate_tests.append((i, j))
    if not candidate_tests:
        return None
    best_test = None
    best_score = -1
    for test in candidate_tests:
        score = calculate_test_score(test, possible_worlds)
        if score > best_score:
            best_score = score
            best_test = test
    return best_test

def filter_worlds(possible_worlds, test, result):
    filtered = []
    for world in possible_worlds:
        expected_result = simulate_test_on_world(test, world)
        if expected_result == result:
            filtered.append(world)
    return filtered

def convert_world_to_tubes(world):
    tubes = []
    for tube_colors in world:
        temp_tube = Tube(0, 0, list(tube_colors))
        temp_tube.colors = list(tube_colors)
        tubes.append(temp_tube)
    return tubes

def check_ready_to_solve(possible_worlds):
    if len(possible_worlds) == 0:
        return False, None
    if len(possible_worlds) == 1:
        return True, possible_worlds[0]
    if len(possible_worlds) <= 5:
        solutions = []
        for world in possible_worlds:
            tubes = convert_world_to_tubes(world)
            sol = solve_bfs(tubes)
            if sol:
                solutions.append(sol)
            else:
                return False, None
        if solutions:
            best_sol = min(solutions, key=lambda s: len(s['path']))
            return True, best_sol
    return False, None

def solve_blind_mode(initial_tubes):
    start_time = time.time()
    num_tubes = len(initial_tubes)
    all_colors_in_game = set()
    for tube in initial_tubes:
        for seg in tube.segments:
            all_colors_in_game.add(seg[0])
    num_colors = len(all_colors_in_game)
    possible_worlds = generate_blind_worlds(num_tubes, num_colors)
    if not possible_worlds:
        print("Failed to generate worlds")
        return None
    print(f"Starting with {len(possible_worlds)} possible worlds")
    tests_performed = []
    nodes = 0
    max_tests = 50
    for test_count in range(max_tests):
        nodes += 1
        test = select_best_test(possible_worlds, initial_tubes)
        if test is None:
            print("No valid tests available")
            break
        from_idx, to_idx = test
        result = "success" if initial_tubes[from_idx].pour(initial_tubes[to_idx]) else "failure"
        tests_performed.append((test, result))
        print(f"Test {test_count + 1}: tube {from_idx} → {to_idx} = {result}")
        possible_worlds = filter_worlds(possible_worlds, test, result)
        print(f"  Remaining worlds: {len(possible_worlds)}")
        if len(possible_worlds) == 0:
            print("✗ No consistent worlds left - puzzle may be unsolvable")
            return None
        ready, solution = check_ready_to_solve(possible_worlds)
        if ready:
            elapsed = time.time() - start_time
            print(f"✓ Ready to solve after {test_count + 1} tests!")
            if isinstance(solution, dict):
                return {
                    'path': solution['path'],
                    'steps': len(solution['path']),
                    'time': elapsed,
                    'nodes': nodes,
                    'tests_performed': len(tests_performed)
                }
            else:
                tubes = convert_world_to_tubes(solution)
                sol = solve_bfs(tubes)
                if sol:
                    return {
                        'path': sol['path'],
                        'steps': len(sol['path']),
                        'time': elapsed,
                        'nodes': nodes,
                        'tests_performed': len(tests_performed)
                    }
    print("✗ Failed to solve within test limit")
    return None

# --- Belief State và And-Or Search ---
class BeliefState:
    def __init__(self, worlds):
        self.worlds = worlds
        self.signature = self._compute_signature()

    def _compute_signature(self):
        sorted_worlds = sorted([tuple(sorted(tuple(tube) for tube in world)) for world in self.worlds])
        return hash(tuple(sorted_worlds))

    def is_goal(self):
        return all(self._is_world_complete(world) for world in self.worlds)

    def _is_world_complete(self, world):
        for tube in world:
            if 0 < len(tube) < 4:
                return False
            if len(tube) == 4 and len(set(tube)) > 1:
                return False
        return True

    def get_valid_actions(self):
        if not self.worlds:
            return []
        visible = self._get_visible_state(self.worlds[0])
        candidate_actions = []
        num_tubes = len(visible)
        for from_idx in range(num_tubes):
            if not visible[from_idx]:
                continue
            for to_idx in range(num_tubes):
                if from_idx == to_idx:
                    continue
                candidate_actions.append((from_idx, to_idx))
        valid_actions = []
        for action in candidate_actions:
            if all(self._is_valid_in_world(action, world) for world in self.worlds):
                valid_actions.append(action)
        return valid_actions

    def _get_visible_state(self, world):
        return tuple((tube[-1],) if tube else () for tube in world)

    def _is_valid_in_world(self, action, world):
        from_idx, to_idx = action
        source_tube = world[from_idx]
        dest_tube = world[to_idx]
        if not source_tube:
            return False
        if len(dest_tube) >= 4:
            return False
        if not dest_tube:
            return True
        top_source = source_tube[-1]
        top_dest = dest_tube[-1]
        return top_source == top_dest

    def apply_action(self, action):
        from_idx, to_idx = action
        new_worlds = []
        for world in self.worlds:
            new_world = [list(tube) for tube in world]
            if self._is_valid_in_world(action, world):
                color = new_world[from_idx].pop()
                new_world[to_idx].append(color)
            new_worlds.append(tuple(tuple(tube) for tube in new_world))
        return BeliefState(new_worlds)

    def size(self):
        return len(self.worlds)

def generate_possible_worlds(tubes, max_worlds=100):
    visible_colors = []
    hidden_counts = []
    for tube in tubes:
        visible = []
        hidden_count = 0
        for color, is_visible in tube.segments:
            if is_visible:
                visible.append(color)
            else:
                hidden_count += 1
        visible_colors.append(tuple(visible))
        hidden_counts.append(hidden_count)
    all_colors = []
    for tube in tubes:
        for color, _ in tube.segments:
            all_colors.append(color)
    color_counts = Counter(all_colors)
    visible_color_counts = Counter()
    for tube_visible in visible_colors:
        for color in tube_visible:
            visible_color_counts[color] += 1
    hidden_available = {}
    for color, total in color_counts.items():
        hidden_available[color] = total - visible_color_counts.get(color, 0)
    hidden_color_pool = []
    for color, count in hidden_available.items():
        hidden_color_pool.extend([color] * count)
    if not hidden_color_pool:
        world = tuple(visible_colors)
        return [world]
    total_hidden_slots = sum(hidden_counts)
    if total_hidden_slots != len(hidden_color_pool):
        return [_generate_simple_world(visible_colors, hidden_counts, hidden_color_pool)]
    unique_perms = set()
    attempts = 0
    max_attempts = max_worlds * 10
    while len(unique_perms) < max_worlds and attempts < max_attempts:
        attempts += 1
        shuffled = hidden_color_pool[:]
        random.shuffle(shuffled)
        world = _distribute_hidden_colors(visible_colors, hidden_counts, shuffled)
        unique_perms.add(world)
    worlds = list(unique_perms)
    if not worlds:
        worlds = [_generate_simple_world(visible_colors, hidden_counts, hidden_color_pool)]
    print(f"Generated {len(worlds)} possible worlds for belief state")
    return worlds

def _distribute_hidden_colors(visible_colors, hidden_counts, color_pool):
    world = []
    pool_index = 0
    for tube_idx, (visible, hidden_count) in enumerate(zip(visible_colors, hidden_counts)):
        hidden_segment = []
        for _ in range(hidden_count):
            if pool_index < len(color_pool):
                hidden_segment.append(color_pool[pool_index])
                pool_index += 1
        tube = tuple(hidden_segment + list(visible))
        world.append(tube)
    return tuple(world)

def _generate_simple_world(visible_colors, hidden_counts, color_pool):
    return _distribute_hidden_colors(visible_colors, hidden_counts, color_pool)

def solve_andor_belief_state(initial_tubes, is_hidden_mode=True):
    start_time = time.time()
    stats = {
        'and_nodes': 0,
        'or_nodes': 0,
        'belief_states_explored': 0,
        'max_belief_size': 0,
        'total_worlds_processed': 0
    }
    if not is_hidden_mode:
        return _solve_andor_classic(initial_tubes, start_time, stats)
    possible_worlds = generate_possible_worlds(initial_tubes, max_worlds=50)
    if not possible_worlds:
        return None
    initial_belief = BeliefState(possible_worlds)
    stats['max_belief_size'] = initial_belief.size()
    visited = set()
    max_depth = 30
    solution_path = _andor_search_recursive(
        initial_belief,
        visited,
        stats,
        depth=0,
        max_depth=max_depth
    )
    elapsed_time = time.time() - start_time
    if solution_path is not None:
        return {
            'path': solution_path,
            'steps': len(solution_path),
            'time': elapsed_time,
            'nodes': stats['and_nodes'],
            'belief_stats': stats
        }
    else:
        return None

def _andor_search_recursive(belief_state, visited, stats, depth, max_depth):
    stats['and_nodes'] += 1
    stats['belief_states_explored'] += 1
    stats['max_belief_size'] = max(stats['max_belief_size'], belief_state.size())
    stats['total_worlds_processed'] += belief_state.size()
    if belief_state.is_goal():
        return []
    if depth > max_depth:
        return None
    if belief_state.signature in visited:
        return None
    visited.add(belief_state.signature)
    valid_actions = belief_state.get_valid_actions()
    if not valid_actions:
        return None
    for action in valid_actions:
        stats['or_nodes'] += 1
        new_belief_state = belief_state.apply_action(action)
        sub_solution = _andor_search_recursive(
            new_belief_state,
            visited,
            stats,
            depth + 1,
            max_depth
        )
        if sub_solution is not None:
            return [action] + sub_solution
    return None

def _solve_andor_classic(initial_tubes, start_time, stats):
    initial_state = tuple(tuple(seg[0] for seg in tube.segments) for tube in initial_tubes)
    visited = set()
    def is_goal(state):
        return all(len(set(tube)) <= 1 and (len(tube) == 0 or len(tube) == 4) for tube in state)
    def get_valid_moves(state):
        moves = []
        for i in range(len(state)):
            if not state[i]:
                continue
            for j in range(len(state)):
                if i == j:
                    continue
                if len(state[j]) >= 4:
                    continue
                if not state[j] or state[j][-1] == state[i][-1]:
                    moves.append((i, j))
        return moves
    def apply_move(state, move):
        from_idx, to_idx = move
        new_state = [list(tube) for tube in state]
        color = new_state[from_idx].pop()
        new_state[to_idx].append(color)
        return tuple(tuple(tube) for tube in new_state)
    def search(state, path):
        stats['and_nodes'] += 1
        if is_goal(state):
            return path
        if state in visited:
            return None
        visited.add(state)
        for move in get_valid_moves(state):
            new_state = apply_move(state, move)
            result = search(new_state, path + [move])
            if result is not None:
                return result
        return None
    solution = search(initial_state, [])
    elapsed_time = time.time() - start_time
    if solution:
        return {
            'path': solution,
            'steps': len(solution),
            'time': elapsed_time,
            'nodes': stats['and_nodes']
        }
    return None

def solve_andor_search(initial_tubes):
    is_hidden = any(not is_visible for tube in initial_tubes for _, is_visible in tube.segments)
    return solve_andor_belief_state(initial_tubes, is_hidden_mode=is_hidden)

# --- Button Class ---
class Button:
    def __init__(self, x, y, width, height, text, action):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.action = action
        self.enabled = True
        self.color = (200, 200, 200)
        self.hover_color = (170, 170, 170)
        self.text_color = (0, 0, 0)
        self.disabled_color = (150, 150, 150)
        self.disabled_text_color = (100, 100, 100)

    def draw(self, screen):
        current_color = self.color
        current_text_color = self.text_color
        if not self.enabled:
            current_color = self.disabled_color
            current_text_color = self.disabled_text_color
        else:
            mouse_pos = pygame.mouse.get_pos()
            if self.rect.collidepoint(mouse_pos):
                current_color = self.hover_color
        pygame.draw.rect(screen, current_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, (100, 100, 100), self.rect, 2, border_radius=8)
        text_surf = FONT_M.render(self.text, True, current_text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def clicked(self, pos):
        if self.enabled and self.rect.collidepoint(pos):
            try:
                if SOUND_CLICK: SOUND_CLICK.play()
            except:
                pass
            return True
        return False

# --- Level Generation ---
def generate_level_by_tube_count(num_color_tubes, game_mode="classic"):
    num_empty_tubes = 2
    capacity = 4
    if num_color_tubes > 8:
        num_color_tubes = 8
    if num_color_tubes > len(ALL_COLORS):
        num_color_tubes = len(ALL_COLORS)
    level_colors = ALL_COLORS[:num_color_tubes]
    solved_state_colors = [[color] * capacity for color in level_colors]
    for _ in range(num_empty_tubes): solved_state_colors.append([])
    num_shuffles = 25 * num_color_tubes
    shuffled_state = [list(t) for t in solved_state_colors]
    for _ in range(num_shuffles):
        try:
            non_empty_indices = [i for i, t in enumerate(shuffled_state) if t]
            from_idx = random.choice(non_empty_indices)
            non_full_indices = [i for i, t in enumerate(shuffled_state) if len(t) < capacity and i != from_idx]
            to_idx = random.choice(non_full_indices)
            color_to_move = shuffled_state[from_idx].pop()
            shuffled_state[to_idx].append(color_to_move)
        except IndexError:
            continue
    all_balls = []
    for tube in shuffled_state: all_balls.extend(tube)
    random.shuffle(all_balls)
    final_state_colors = [[] for _ in range(num_color_tubes)]
    for ball in all_balls:
        while True:
            target_idx = random.randrange(num_color_tubes)
            if len(final_state_colors[target_idx]) < capacity:
                final_state_colors[target_idx].append(ball)
                break
    for _ in range(num_empty_tubes): final_state_colors.append([])
    final_tubes = []
    num_total_tubes = len(final_state_colors)
    num_rows = (num_total_tubes + TUBES_PER_ROW - 1) // TUBES_PER_ROW
    for i in range(num_total_tubes):
        row = i // TUBES_PER_ROW
        col = i % TUBES_PER_ROW
        tubes_in_this_row = min(TUBES_PER_ROW, num_total_tubes - row * TUBES_PER_ROW)
        total_width_of_row = tubes_in_this_row * TUBE_WIDTH + (tubes_in_this_row - 1) * TUBE_SPACING
        start_x = (WIDTH - total_width_of_row - 250) // 2
        y_offset = (HEIGHT - (num_rows * TUBE_HEIGHT + (num_rows - 1) * 50)) // 2
        x_pos = start_x + col * (TUBE_WIDTH + TUBE_SPACING)
        y_pos = y_offset + row * (TUBE_HEIGHT + 50)
        is_hidden = (game_mode == "hidden")
        is_blind = (game_mode == "blind")
        final_tubes.append(Tube(
            x_pos, y_pos,
            final_state_colors[i],
            is_hidden_mode=is_hidden,
            is_blind_mode=is_blind
        ))
    return final_tubes

def check_win(current_tubes):
    for tube in current_tubes:
        if 0 < len(tube.segments) < 4:
            return False
        if len(tube.segments) == 4:
            first_color = tube.segments[0][0]
            for segment in tube.segments[1:]:
                if segment[0] != first_color:
                    return False
    return True

# --- Solution Path Viewer ---
class SolutionViewer:
    def __init__(self):
        self.visible = False
        self.current_algorithm = None
        self.current_step = 0
        self.solution_path = []
        self.viewer_tubes = []
        self.step_description = ""
        self.initial_tubes_backup = []

    def show(self, algorithm_name, solution_data, initial_tubes):
        self.visible = True
        self.current_algorithm = algorithm_name
        self.current_step = 0
        self.solution_path = solution_data.get('path', [])
        self.step_description = ""
        self.initial_tubes_backup = []
        for tube in initial_tubes:
            colors = [seg[0] for seg in tube.segments]
            temp_tube = Tube(tube.x, tube.y, colors)
            temp_tube.colors = colors.copy()
            self.initial_tubes_backup.append(temp_tube)
        self.viewer_tubes = []
        for tube in self.initial_tubes_backup:
            colors = [seg[0] for seg in tube.segments]
            new_tube = Tube(tube.x, tube.y, colors)
            new_tube.colors = colors.copy()
            self.viewer_tubes.append(new_tube)
        self.update_step_description()

    def hide(self):
        self.visible = False

    def next_step(self):
        if self.current_step < len(self.solution_path):
            from_idx, to_idx = self.solution_path[self.current_step]
            if from_idx < len(self.viewer_tubes) and to_idx < len(self.viewer_tubes):
                self.viewer_tubes[from_idx].pour(self.viewer_tubes[to_idx])
            self.current_step += 1
            self.update_step_description()

    def prev_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.reset_to_initial()
            for i in range(self.current_step):
                from_idx, to_idx = self.solution_path[i]
                if from_idx < len(self.viewer_tubes) and to_idx < len(self.viewer_tubes):
                    self.viewer_tubes[from_idx].pour(self.viewer_tubes[to_idx])
            self.update_step_description()

    def reset_to_initial(self):
        self.viewer_tubes = []
        for tube in self.initial_tubes_backup:
            colors = [seg[0] for seg in tube.segments]
            new_tube = Tube(tube.x, tube.y, colors)
            new_tube.colors = colors.copy()
            self.viewer_tubes.append(new_tube)

    def update_step_description(self):
        total_steps = len(self.solution_path)
        if self.current_step < total_steps:
            from_idx, to_idx = self.solution_path[self.current_step]
            self.step_description = f"Step {self.current_step + 1}/{total_steps}: Tube {from_idx} → Tube {to_idx}"
        else:
            self.step_description = f"Complete! Total steps: {total_steps}"

    def draw(self, screen):
        if not self.visible:
            return
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        num_tubes = len(self.viewer_tubes)
        panel_width = min(800, WIDTH - 100)
        panel_height = min(700, HEIGHT - 100)
        panel_x = (WIDTH - panel_width) // 2
        panel_y = 50
        pygame.draw.rect(screen, (240, 240, 240), (panel_x, panel_y, panel_width, panel_height), border_radius=20)
        pygame.draw.rect(screen, (100, 100, 100), (panel_x, panel_y, panel_width, panel_height), 3, border_radius=20)
        title_text = FONT_L.render(f"{self.current_algorithm} Solution", True, BLACK)
        title_rect = title_text.get_rect(center=(WIDTH // 2, panel_y + 40))
        screen.blit(title_text, title_rect)
        step_text = FONT_M.render(self.step_description, True, BLUE_HIGHLIGHT)
        step_rect = step_text.get_rect(center=(WIDTH // 2, panel_y + 90))
        screen.blit(step_text, step_rect)
        tubes_per_row = min(5, num_tubes)
        num_rows = (num_tubes + tubes_per_row - 1) // tubes_per_row
        viewer_tube_width = 60
        viewer_tube_height = 180
        tube_spacing = 15
        total_viewer_width = tubes_per_row * viewer_tube_width + (tubes_per_row - 1) * tube_spacing
        start_x = panel_x + (panel_width - total_viewer_width) // 2
        start_y = panel_y + 130
        for i, tube in enumerate(self.viewer_tubes):
            row = i // tubes_per_row
            col = i % tubes_per_row
            x_pos = start_x + col * (viewer_tube_width + tube_spacing)
            y_pos = start_y + row * (viewer_tube_height + 40)
            self.draw_tube_small(screen, tube, x_pos, y_pos, viewer_tube_width, viewer_tube_height)
            tube_number = FONT_S.render(str(i), True, BLACK)
            number_rect = tube_number.get_rect(center=(x_pos + viewer_tube_width // 2, y_pos + viewer_tube_height + 15))
            screen.blit(tube_number, number_rect)
        control_y = panel_y + panel_height - 80
        prev_color = (150, 150, 150) if self.current_step == 0 else (100, 100, 255)
        pygame.draw.rect(screen, prev_color, (panel_x + 50, control_y, 100, 40), border_radius=8)
        prev_text = FONT_M.render("Previous", True, WHITE)
        prev_rect = prev_text.get_rect(center=(panel_x + 100, control_y + 20))
        screen.blit(prev_text, prev_rect)
        next_color = (150, 150, 150) if self.current_step >= len(self.solution_path) else (100, 255, 100)
        pygame.draw.rect(screen, next_color, (panel_x + panel_width - 150, control_y, 100, 40), border_radius=8)
        next_text = FONT_M.render("Next", True, WHITE)
        next_rect = next_text.get_rect(center=(panel_x + panel_width - 100, control_y + 20))
        screen.blit(next_text, next_rect)
        close_x = panel_x + (panel_width - 100) // 2
        pygame.draw.rect(screen, (255, 100, 100), (close_x, control_y, 100, 40), border_radius=8)
        close_text = FONT_M.render("Close", True, WHITE)
        close_rect = close_text.get_rect(center=(close_x + 50, control_y + 20))
        screen.blit(close_text, close_rect)

    def draw_tube_small(self, screen, tube, x, y, width, height):
        pygame.draw.rect(screen, (180, 180, 180), (x, y, width, height), border_radius=6)
        water_width = width - 12
        water_height = (height - 20) // CAPACITY
        water_x = x + 6
        for i, (color, is_visible) in enumerate(tube.segments):
            water_y = y + height - 10 - (i + 1) * water_height
            draw_color = color if is_visible else GREY
            pygame.draw.rect(screen, draw_color, (water_x, water_y, water_width, water_height), border_radius=3)
            if not is_visible:
                q_mark_surf = FONT_S.render('?', True, WHITE)
                segment_rect = pygame.Rect(water_x, water_y, water_width, water_height)
                q_mark_rect = q_mark_surf.get_rect(center=segment_rect.center)
                screen.blit(q_mark_surf, q_mark_rect)

    def handle_click(self, pos):
        if not self.visible:
            return False
        num_tubes = len(self.viewer_tubes)
        panel_width = min(800, WIDTH - 100)
        panel_height = min(700, HEIGHT - 100)
        panel_x = (WIDTH - panel_width) // 2
        panel_y = 50
        control_y = panel_y + panel_height - 80
        prev_rect = pygame.Rect(panel_x + 50, control_y, 100, 40)
        if prev_rect.collidepoint(pos) and self.current_step > 0:
            self.prev_step()
            return True
        next_rect = pygame.Rect(panel_x + panel_width - 150, control_y, 100, 40)
        if next_rect.collidepoint(pos) and self.current_step < len(self.solution_path):
            self.next_step()
            return True
        close_x = panel_x + (panel_width - 100) // 2
        close_rect = pygame.Rect(close_x, control_y, 100, 40)
        if close_rect.collidepoint(pos):
            self.hide()
            return True
        return False

# --- Main Game ---
def main_game():
    game_mode = "classic"
    num_color_tubes = 4
    tubes = []
    initial_tubes = []
    selected_tube = None
    win = False
    auto_play = False
    current_algorithm = None
    solutions = {}
    show_compare = False
    stuck_message = ""
    last_move_time = 0
    current_step = 0
    solution_viewer = SolutionViewer()

    def setup_level(color_tubes_count, mode):
        nonlocal tubes, initial_tubes, win, auto_play, solutions, show_compare, selected_tube, stuck_message
        print(f"Generating level with {color_tubes_count} color tubes in {mode} mode...")
        tubes = generate_level_by_tube_count(color_tubes_count, mode)
        initial_tubes = []
        for t in tubes:
            colors = [seg[0] for seg in t.segments]
            initial_tubes.append(
                Tube(t.x, t.y, colors, is_hidden_mode=(mode == "hidden"), is_blind_mode=(mode == "blind")))
        win = False
        auto_play = False
        solutions.clear()
        show_compare = False
        selected_tube = None
        stuck_message = ""
        print("Level generated.")

    setup_level(num_color_tubes, game_mode)

    ui_panel_x = 1050
    level_buttons = [
        Button(ui_panel_x, 120, 220, 40, "Generate New Level", "generate"),
        Button(ui_panel_x, 170, 220, 40, "Reset Current Level", "reset"),
        Button(ui_panel_x + 170, 70, 50, 40, "+", "increase_tubes"),
        Button(ui_panel_x, 70, 50, 40, "-", "decrease_tubes"),
    ]
    mode_toggle_button = Button(ui_panel_x, 220, 220, 40, f"Mode: {game_mode.title()}", "toggle_mode")
    solver_buttons = [
        Button(ui_panel_x, 290, 220, 40, "BFS Solve", "bfs"),
        Button(ui_panel_x, 340, 220, 40, "DFS Solve", "dfs"),
        Button(ui_panel_x, 390, 220, 40, "A* Solve", "a_star"),
        Button(ui_panel_x, 440, 220, 40, "Greedy Solve", "greedy"),
        Button(ui_panel_x, 490, 220, 40, "SA Solve", "sa"),
        Button(ui_panel_x, 540, 220, 40, "HC+Restarts Solve", "hill_climb"),
        Button(ui_panel_x, 590, 220, 40, "Backtracking Solve", "backtracking"),
        Button(ui_panel_x, 640, 220, 40, "ABCA Solve", "abca"),
        Button(ui_panel_x, 690, 220, 40, "And-Or Solve", "and_or"),
    ]
    compare_button = Button(ui_panel_x, 740, 220, 40, "Compare All Results", "compare")
    view_solution_button = Button(ui_panel_x, 790, 220, 40, "View Solution Path", "view_solution")

    all_buttons = level_buttons + [mode_toggle_button] + solver_buttons + [compare_button, view_solution_button]

    running = True
    clock = pygame.time.Clock()
    current_time = time.time()

    while running:
        current_time = time.time()

        def update_button_states_fixed(solver_buttons, game_mode):
            for button in solver_buttons:
                if button.action == "and_or":
                    button.enabled = (game_mode in ["hidden", "blind", "classic"])
                elif button.action == "blind":
                    button.enabled = (game_mode == "blind")
                else:
                    button.enabled = (game_mode == "classic")

        update_button_states_fixed(solver_buttons, game_mode)
        mode_toggle_button.text = f"Mode: {game_mode.title()}"

        view_solution_button.enabled = (current_algorithm is not None and current_algorithm in solutions)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if solution_viewer.visible:
                    if solution_viewer.handle_click(pos):
                        continue
                for button in all_buttons:
                    if button.clicked(pos):
                        if button.action == "generate":
                            setup_level(num_color_tubes, game_mode)
                        elif button.action == "reset":
                            is_hidden = (game_mode == "hidden")
                            is_blind = (game_mode == "blind")
                            tubes = []
                            for t in initial_tubes:
                                colors = [seg[0] for seg in t.segments]
                                tubes.append(Tube(t.x, t.y, colors, is_hidden_mode=is_hidden, is_blind_mode=is_blind))
                            win = False
                            auto_play = False
                            selected_tube = None
                            stuck_message = ""
                        elif button.action == "increase_tubes":
                            if num_color_tubes < 8:
                                num_color_tubes += 1
                                setup_level(num_color_tubes, game_mode)
                        elif button.action == "decrease_tubes":
                            if num_color_tubes > 3:
                                num_color_tubes -= 1
                                setup_level(num_color_tubes, game_mode)
                        elif button.action == "toggle_mode":
                            if game_mode == "classic":
                                game_mode = "hidden"
                            elif game_mode == "hidden":
                                game_mode = "blind"
                            else:
                                game_mode = "classic"
                            setup_level(num_color_tubes, game_mode)
                        elif button.action == "compare":
                            if len(solutions) > 0: show_compare = not show_compare
                        elif button.action == "view_solution":
                            if current_algorithm and current_algorithm in solutions:
                                solution_viewer.show(current_algorithm, solutions[current_algorithm], initial_tubes)
                        elif button.action in ["bfs", "dfs", "a_star", "sa", "greedy", "and_or", "hill_climb", "backtracking", "abca"]:
                            if not auto_play and not win:
                                stuck_message = ""
                                alg_map = {
                                    "bfs": ("BFS", solve_bfs), "dfs": ("DFS", solve_dfs),
                                    "a_star": ("A*", solve_a_star), "greedy": ("Greedy", solve_greedy),
                                    "and_or": ("And-Or", solve_andor_search), "sa": ("SA", solve_sa),
                                    "hill_climb": ("HC+Restarts", solve_hill_climb_restarts),
                                    "backtracking": ("Backtracking", solve_backtracking), "abca": ("ABCA", solve_abca)
                                }
                                alg_name, solve_func = alg_map[button.action]
                                print(f"Solving with {alg_name}...")
                                compatible_initial_tubes = []
                                for t in initial_tubes:
                                    temp_tube = Tube(t.x, t.y, [seg[0] for seg in t.segments])
                                    temp_tube.colors = [seg[0] for seg in t.segments]
                                    compatible_initial_tubes.append(temp_tube)
                                result = solve_func(compatible_initial_tubes)
                                if result:
                                    solutions[alg_name] = result
                                    current_algorithm = alg_name
                                    if result.get('path'):
                                        auto_play = True
                                        current_step = 0
                                        is_hidden = (game_mode == "hidden")
                                        is_blind = (game_mode == "blind")
                                        tubes = []
                                        for t in initial_tubes:
                                            colors = [seg[0] for seg in t.segments]
                                            tubes.append(Tube(t.x, t.y, colors, is_hidden_mode=is_hidden, is_blind_mode=is_blind))
                                    if result.get('stuck', False):
                                        stuck_message = f"{alg_name} got stuck after {result['steps']} moves."
                                        print(f"{alg_name} animation will play until the stuck point.")
                                    else:
                                        print(f"{alg_name} solution found: {result['steps']} steps in {result['time']:.3f}s, {result['nodes']} nodes explored.")
                                else:
                                    stuck_message = f"No solution found with {alg_name}."
                                    print(f"No solution found with {alg_name}")
                if not auto_play and not win and not show_compare and not solution_viewer.visible:
                    for i, tube in enumerate(tubes):
                        if tube.rect.collidepoint(pos):
                            if selected_tube is None:
                                if tube.segments:
                                    selected_tube = i
                                    tube.is_selected = True
                                    try:
                                        if SOUND_SELECT: SOUND_SELECT.play()
                                    except:
                                        pass
                            else:
                                if i == selected_tube:
                                    tubes[selected_tube].is_selected = False
                                    selected_tube = None
                                else:
                                    source, dest = tubes[selected_tube], tubes[i]
                                    if source.pour(dest):
                                        if check_win(tubes):
                                            win = True
                                            try:
                                                if SOUND_WIN: SOUND_WIN.play()
                                            except:
                                                pass
                                    tubes[selected_tube].is_selected = False
                                    selected_tube = None
                            break
        for t in tubes:
            t.update()
        if auto_play and current_algorithm in solutions and current_step < len(solutions[current_algorithm]['path']):
            if current_time - last_move_time >= AUTO_PLAY_DELAY:
                from_tube, to_tube = solutions[current_algorithm]['path'][current_step]
                source, dest = tubes[from_tube], tubes[to_tube]
                if source.pour(dest):
                    current_step += 1
                    last_move_time = current_time
                    if check_win(tubes):
                        win = True
                        auto_play = False
                        try:
                            if SOUND_WIN: SOUND_WIN.play()
                        except:
                            pass
        elif auto_play and not win:
            auto_play = False
        if BG_IMG:
            screen.blit(BG_IMG, (0, 0))
        else:
            screen.fill((220, 220, 220))
        panel_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(panel_surface, PANEL_BG, (ui_panel_x - 10, 0, WIDTH - ui_panel_x + 10, HEIGHT),
                         border_top_left_radius=20, border_bottom_left_radius=20)
        screen.blit(panel_surface, (0, 0))
        for tube in tubes:
            tube.draw(screen)
        if selected_tube is not None and not auto_play:
            pygame.draw.rect(screen, BLUE_HIGHLIGHT, tubes[selected_tube].rect, 4, border_radius=5)
        title_font = FONT_L
        panel_title = title_font.render("CONTROLS", True, (0, 0, 0))
        screen.blit(panel_title, (ui_panel_x, 20))
        for button in all_buttons:
            button.draw(screen)
        num_tubes_text = FONT_M.render(f"{num_color_tubes} Colors", True, (0, 0, 0))
        num_tubes_rect = num_tubes_text.get_rect(center=(ui_panel_x + 110, 90))
        screen.blit(num_tubes_text, num_tubes_rect)
        if win:
            win_text = FONT_L.render("YOU WIN!", True, GREEN)
            win_rect = win_text.get_rect(center=(WIDTH // 2, 50))
            pygame.draw.rect(screen, (*WHITE, 200), win_rect.inflate(20, 20), border_radius=15)
            screen.blit(win_text, win_rect)
        elif auto_play and current_algorithm:
            text = f"Playing {current_algorithm}: Step {current_step}/{solutions[current_algorithm]['steps']}"
            step_text = FONT_M.render(text, True, BLUE_HIGHLIGHT)
            screen.blit(step_text, (20, 20))
        elif stuck_message and not auto_play and not win:
            stuck_text_surf = FONT_M.render(stuck_message, True, (200, 0, 0))
            screen.blit(stuck_text_surf, (20, 20))
        if show_compare:
            overlay = pygame.Surface((ui_panel_x - 10, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, 220))
            screen.blit(overlay, (0, 0))
            y = 60
            compare_title = FONT_M.render("Comparison:", True, (0, 0, 0))
            screen.blit(compare_title, (20, y))
            y += 40
            sorted_solutions = sorted(solutions.items(), key=lambda item: item[1]['steps'])
            for alg, res in sorted_solutions:
                text = f"• {alg}: Steps={res['steps']}, Time={res['time']:.3f}s, Nodes={res['nodes']}"
                text_surf = FONT_S.render(text, True, (0, 0, 0))
                screen.blit(text_surf, (20, y))
                y += 30
        solution_viewer.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)
    pygame.quit()

if __name__ == "__main__":
    main_game()