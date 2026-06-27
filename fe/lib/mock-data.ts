export const mockArchetypes = [
  { id: 'human', name: 'Human', icon: '👤', category: 'Humanoid' },
  { id: 'athlete', name: 'Athlete', icon: '🏃‍♀️', category: 'Humanoid' },
  { id: 'orc_warrior', name: 'Orc Warrior', icon: '👹', category: 'Fantasy' },
  { id: 'elf_archer', name: 'Elf Archer', icon: '🧝', category: 'Fantasy' },
  { id: 'wizard', name: 'Wizard', icon: '🧙', category: 'Fantasy' },
  { id: 'robot', name: 'Robot', icon: '🤖', category: 'Sci-Fi' },
];

export const mockEnsembles = [
  { id: 'tennis_uniform', name: 'Tennis Outfit', icon: '🎾' },
  { id: 'business_suit', name: 'Business Suit', icon: '👔' },
  { id: 'wizard_attire', name: 'Wizard Robe', icon: '🧙' },
  { id: 'plate_armor', name: 'Plate Armor', icon: '⚔️' },
  { id: 'casual', name: 'Casual', icon: '👕' },
];

export const mockAtmospheres = [
  {
    id: 'beach',
    name: 'Beach',
    icon: '🏖️',
    preset: 'beach',
    ground: 'Soft sandy shore',
    envelope: 'Golden sunset',
    vista: 'Ocean waves',
    background: 'Seabirds gliding',
  },
  {
    id: 'cafe',
    name: 'Cafe',
    icon: '☕',
    preset: 'cafe',
    ground: 'Polished wood',
    envelope: 'Warm indoor lighting',
    vista: 'Large windows',
    background: 'Patrons chatting',
  },
  {
    id: 'alley',
    name: 'Neon Alley',
    icon: '🌆',
    preset: 'alley',
    ground: 'Wet cobblestone',
    envelope: 'Dim neon lights',
    vista: 'City skyline',
    background: 'Pedestrians in distance',
  },
  {
    id: 'forest',
    name: 'Forest',
    icon: '🌳',
    preset: 'forest',
    ground: 'Moss and grass',
    envelope: 'Natural dappled light',
    vista: 'Forest canopy',
    background: 'Distant birds',
  },
  {
    id: 'office',
    name: 'Office',
    icon: '💼',
    preset: 'office',
    ground: 'Carpet floor',
    envelope: 'Fluorescent lights',
    vista: 'Cubicles',
    background: 'Office noise',
  },
  {
    id: 'rooftop',
    name: 'Rooftop',
    icon: '🏢',
    preset: 'rooftop',
    ground: 'Concrete roof',
    envelope: 'Evening starlight',
    vista: 'Skyscrapers',
    background: 'City traffic below',
  },
  {
    id: 'pool',
    name: 'Poolside',
    icon: '🏊',
    preset: 'pool',
    ground: 'Tiled deck',
    envelope: 'Shimmering sunbeams',
    vista: 'Deep blue water',
    background: 'Splash ripples',
  },
  {
    id: 'balcony',
    name: 'Balcony',
    icon: '🌅',
    preset: 'balcony',
    ground: 'Terracotta tiles',
    envelope: 'Sunrise glow',
    vista: 'Scenic valley',
    background: 'Gentle breeze',
  },
  {
    id: 'bedroom',
    name: 'Bedroom',
    icon: '🛏️',
    preset: 'bedroom',
    ground: 'Plush carpet',
    envelope: 'Soft bedside lamp',
    vista: 'Cozy walls',
    background: 'Quiet peace',
  },
  {
    id: 'bathroom',
    name: 'Bathroom',
    icon: '🛁',
    preset: 'bathroom',
    ground: 'White marble',
    envelope: 'Bright vanity mirror',
    vista: 'Steamy glass',
    background: 'Dripping faucet',
  },
];

export const mockRelationshipTypes = [
  { id: 'holding', name: 'Holding', icon: '🤝', targetType: 'prop' },
  { id: 'leaning', name: 'Leaning On', icon: '🤝', targetType: 'prop' },
  { id: 'proposal', name: 'Proposal', icon: '💍', targetType: 'none' },
  { id: 'fighting', name: 'Fighting', icon: '⚔️', targetType: 'none' },
  { id: 'framing', name: 'Framing', icon: '🖼️', targetType: 'prop' },
];

export const mockProps = [
  {
    id: 'rose_arch',
    name: 'Rose Arch',
    icon: '🌹',
    type: 'arch',
    label: 'Massive heart-shaped arch',
    details: 'Made entirely of red roses with glowing text',
  },
  {
    id: 'bench',
    name: 'Bench',
    icon: '🪑',
    type: 'bench',
    label: 'Wooden park bench',
    details: 'Old weathered wood with faded paint',
  },
  {
    id: 'table',
    name: 'Table',
    icon: '🛏️',
    type: 'table',
    label: 'Round bistro table',
    details: 'Wrought iron with marble top',
  },
  {
    id: 'wall',
    name: 'Wall',
    icon: '🧱',
    type: 'wall',
    label: 'Whitewashed stone wall',
    details: 'Ancient brick with ivy climbing',
  },
  {
    id: 'tree',
    name: 'Tree',
    icon: '🌳',
    type: 'tree',
    label: 'Ancient oak tree',
    details: 'Gnarled branches with deep roots',
  },
];

export const mockCameraProfiles = [
  { id: 'close_up', name: 'Close-up' },
  { id: 'medium', name: 'Medium' },
  { id: 'full_body', name: 'Full-body' },
  { id: 'wide', name: 'Wide' },
  { id: 'low_angle', name: 'Low-angle' },
];

export const mockRenderProfiles = [
  { id: 'cinematic', name: 'Cinematic' },
  { id: 'commercial', name: 'Commercial' },
  { id: 'editorial', name: 'Editorial' },
  { id: 'portrait', name: 'Portrait' },
];

export const mockExpressions = [
  'Neutral',
  'Smiling',
  'Serious',
  'Surprised',
  'Angry',
  'Laughing',
];

export const mockHairStyles = [
  'Ponytail',
  'Braids',
  'Wavy',
  'Curly',
  'Straight',
  'Bun',
];

export const mockHairColors = [
  'Brown',
  'Blonde',
  'Black',
  'Red',
  'Silver',
  'Auburn',
];

export const mockHairLengths = [
  'Short',
  'Medium',
  'Long',
];

export const mockClothingGarments = [
  'Polo Shirt',
  'T-Shirt',
  'Dress Shirt',
  'Sweater',
  'Tank Top',
];

export const mockClothingColors = [
  'White',
  'Black',
  'Blue',
  'Red',
  'Green',
  'Grey',
];

export const mockPoses = [
  'Standing',
  'Sitting',
  'Kneeling',
  'Crouching',
  'Lying',
];

export const mockGazeDirections = [
  'Toward Camera',
  'Away',
  'Down',
  'Up',
  'To the Side',
];

export const mockArmPositions = [
  'At Side',
  'Crossed',
  'Raised',
  'Behind Back',
];

export const mockLegPositions = [
  'Standing',
  'Crossed',
  'Apart',
  'Bent',
];

export const mockCameraFramings = [
  'Close-up',
  'Medium',
  'Full-body',
  'Wide',
];

export const mockCameraAngles = [
  'Eye-level',
  'Low-angle',
  'High-angle',
  'Dutch',
  'Overhead',
];

export const mockLenses = [
  '24mm',
  '35mm',
  '50mm',
  '85mm',
  '105mm',
];

export const mockDepthOfFields = [
  'Shallow',
  'Medium',
  'Deep',
];

export const mockMoods = [
  'Neutral',
  'Dramatic',
  'Romantic',
  'Dark',
  'Bright',
  'Melancholic',
];

// WARDROBE DATA - Ensembles (Full Outfits)
export const mockEnsemblesDetailed = [
  {
    id: 'tennis_uniform',
    name: 'Tennis Outfit',
    icon: '🎾',
    description: 'Classic tennis player uniform',
    clothing: {
      upper_body: { garment: 'Polo Shirt', color: 'White', fit: 'Athletic', material: 'Performance' },
      lower_body: { garment: 'Tennis Shorts', color: 'White', fit: 'Athletic', material: 'Performance' },
      feet: { garment: 'Tennis Shoes', color: 'White', fit: 'Standard', material: 'Mesh' },
      hands: { garment: 'None', color: 'Skin', fit: 'Standard', material: 'Natural' },
      headwear: { garment: 'Visor', color: 'White', fit: 'Adjustable', material: 'Cotton' },
    },
  },
  {
    id: 'business_suit',
    name: 'Business Suit',
    icon: '👔',
    description: 'Professional business attire',
    clothing: {
      upper_body: { garment: 'Dress Shirt', color: 'White', fit: 'Tailored', material: 'Cotton' },
      lower_body: { garment: 'Dress Pants', color: 'Black', fit: 'Tailored', material: 'Wool' },
      feet: { garment: 'Dress Shoes', color: 'Black', fit: 'Standard', material: 'Leather' },
      hands: { garment: 'Tie', color: 'Navy', fit: 'Standard', material: 'Silk' },
      headwear: { garment: 'None', color: 'Natural', fit: 'Standard', material: 'Natural' },
    },
  },
  {
    id: 'wizard_attire',
    name: 'Wizard Robe',
    icon: '🧙',
    description: 'Mystical wizard outfit',
    clothing: {
      upper_body: { garment: 'Wizard Robe', color: 'Purple', fit: 'Loose', material: 'Velvet' },
      lower_body: { garment: 'Wizard Robe', color: 'Purple', fit: 'Loose', material: 'Velvet' },
      feet: { garment: 'Pointed Shoes', color: 'Purple', fit: 'Standard', material: 'Leather' },
      hands: { garment: 'Gloves', color: 'Purple', fit: 'Fitted', material: 'Silk' },
      headwear: { garment: 'Pointy Hat', color: 'Purple', fit: 'Standard', material: 'Velvet' },
    },
  },
  {
    id: 'plate_armor',
    name: 'Plate Armor',
    icon: '⚔️',
    description: 'Full medieval plate armor',
    clothing: {
      upper_body: { garment: 'Plate Armor', color: 'Steel', fit: 'Armor', material: 'Metal' },
      lower_body: { garment: 'Leg Plates', color: 'Steel', fit: 'Armor', material: 'Metal' },
      feet: { garment: 'Armored Boots', color: 'Steel', fit: 'Armor', material: 'Metal' },
      hands: { garment: 'Gauntlets', color: 'Steel', fit: 'Armor', material: 'Metal' },
      headwear: { garment: 'Helmet', color: 'Steel', fit: 'Armor', material: 'Metal' },
    },
  },
  {
    id: 'casual_beach',
    name: 'Casual Beach',
    icon: '🏖️',
    description: 'Relaxed beachwear',
    clothing: {
      upper_body: { garment: 'T-Shirt', color: 'Light Blue', fit: 'Relaxed', material: 'Cotton' },
      lower_body: { garment: 'Shorts', color: 'Khaki', fit: 'Relaxed', material: 'Cotton' },
      feet: { garment: 'Sandals', color: 'Tan', fit: 'Standard', material: 'Rubber' },
      hands: { garment: 'None', color: 'Skin', fit: 'Standard', material: 'Natural' },
      headwear: { garment: 'None', color: 'Natural', fit: 'Standard', material: 'Natural' },
    },
  },
];

// WARDROBE DATA - Individual Garments
export const mockGarments = {
  upper_body: [
    { id: 'polo_shirt', name: 'Polo Shirt', colors: ['White', 'Navy', 'Red', 'Black'] },
    { id: 'tshirt', name: 'T-Shirt', colors: ['White', 'Black', 'Gray', 'Light Blue'] },
    { id: 'dress_shirt', name: 'Dress Shirt', colors: ['White', 'Light Blue', 'Pink'] },
    { id: 'sweater', name: 'Sweater', colors: ['Navy', 'Cream', 'Brown', 'Black'] },
    { id: 'hoodie', name: 'Hoodie', colors: ['Black', 'Gray', 'Navy', 'White'] },
    { id: 'bikini_top', name: 'Bikini Top', colors: ['Red', 'Blue', 'Black', 'White'] },
    { id: 'crop_top', name: 'Crop Top', colors: ['Black', 'White', 'Gold'] },
    { id: 'tank_top', name: 'Tank Top', colors: ['White', 'Black', 'Gray'] },
    { id: 'button_up', name: 'Button Up Shirt', colors: ['White', 'Black', 'Plaid'] },
    { id: 'blouse', name: 'Blouse', colors: ['White', 'Cream', 'Burgundy'] },
  ],
  lower_body: [
    { id: 'jeans', name: 'Jeans', colors: ['Blue', 'Black', 'Light Blue'] },
    { id: 'shorts', name: 'Shorts', colors: ['Khaki', 'Black', 'Denim', 'White'] },
    { id: 'dress_pants', name: 'Dress Pants', colors: ['Black', 'Gray', 'Navy'] },
    { id: 'skirt', name: 'Skirt', colors: ['Black', 'Red', 'Plaid', 'White'] },
    { id: 'leggings', name: 'Leggings', colors: ['Black', 'Gray', 'Navy'] },
    { id: 'athletic_shorts', name: 'Athletic Shorts', colors: ['Black', 'White', 'Navy'] },
    { id: 'cargo_pants', name: 'Cargo Pants', colors: ['Khaki', 'Black', 'Olive'] },
  ],
  feet: [
    { id: 'sneakers', name: 'Sneakers', colors: ['White', 'Black', 'Gray'] },
    { id: 'dress_shoes', name: 'Dress Shoes', colors: ['Black', 'Brown', 'Oxblood'] },
    { id: 'boots', name: 'Boots', colors: ['Black', 'Brown', 'Tan'] },
    { id: 'sandals', name: 'Sandals', colors: ['Tan', 'Black', 'Brown'] },
    { id: 'heels', name: 'Heels', colors: ['Black', 'Red', 'Nude'] },
    { id: 'running_shoes', name: 'Running Shoes', colors: ['White', 'Black', 'Blue'] },
  ],
  hands: [
    { id: 'none', name: 'None', colors: ['Natural'] },
    { id: 'gloves', name: 'Gloves', colors: ['Black', 'White', 'Brown'] },
    { id: 'leather_gloves', name: 'Leather Gloves', colors: ['Black', 'Brown'] },
    { id: 'ring', name: 'Ring', colors: ['Gold', 'Silver'] },
  ],
  headwear: [
    { id: 'none', name: 'None', colors: ['Natural'] },
    { id: 'baseball_cap', name: 'Baseball Cap', colors: ['Black', 'White', 'Navy'] },
    { id: 'beanie', name: 'Beanie', colors: ['Black', 'Gray', 'Navy'] },
    { id: 'hat', name: 'Hat', colors: ['Black', 'Tan', 'Brown'] },
    { id: 'visor', name: 'Visor', colors: ['White', 'Black', 'Navy'] },
  ],
};
