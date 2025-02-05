import ollama from 'ollama'

let start = performance.now();
const response = await ollama.chat({
  model: 'llama3.2-vision',
  messages: [{
    role: 'user',
    content: 'you are an expert at describing the following image',
    images: ['image.png']
  }]
})
let end = performance.now();

console.log(response)
console.log((end-start)/(1000*60))