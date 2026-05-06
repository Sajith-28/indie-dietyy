// Lightweight canned plan response for Vercel serverless (free fallback)
// POST /api/generate_plan
module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method Not Allowed' });
    return;
  }

  // Parse incoming body safely
  let body = {};
  try {
    body = req.body || {};
  } catch (e) {
    // ignore
  }

  // Minimal canned plan matching frontend shape
  const plan = {
    metadata: {
      user_name: body.name || 'Guest',
      bmi: 22.5,
      medical_classifications: {},
      active_ai_models: [],
      title: 'Demo 7-Day Precision Diet Plan',
      disclaimer: 'This is a demo plan. The real AI backend is required for clinical use.'
    },
    diet_plan: {
      'Day 1': {
        Breakfast: {
          meal_name: 'Poha with Peanuts',
          calories: 320,
          protein_g: 10,
          carbs_g: 45,
          fat_g: 11,
          fiber_g: 5,
          ingredients: 'Poha, peanuts, mustard seeds, curry leaves',
          ai_score: 92
        },
        Lunch: {
          meal_name: 'Vegetable Sambar with Rice',
          calories: 610,
          protein_g: 16,
          carbs_g: 98,
          fat_g: 12,
          fiber_g: 8,
          ingredients: 'Rice, lentils, mixed vegetables, tamarind',
          ai_score: 90
        },
        Snack: {
          meal_name: 'Buttermilk & Fruit',
          calories: 160,
          protein_g: 4,
          carbs_g: 28,
          fat_g: 3,
          fiber_g: 2,
          ingredients: 'Buttermilk, seasonal fruit',
          ai_score: 85
        },
        Dinner: {
          meal_name: 'Chapati with Vegetable Curry',
          calories: 480,
          protein_g: 12,
          carbs_g: 70,
          fat_g: 14,
          fiber_g: 7,
          ingredients: 'Wheat, mixed vegetables, spices',
          ai_score: 88
        }
      },
      'Day 2': {},
      'Day 3': {},
      'Day 4': {},
      'Day 5': {},
      'Day 6': {},
      'Day 7': {}
    }
  };

  res.setHeader('Content-Type', 'application/json');
  res.status(200).json(plan);
};
