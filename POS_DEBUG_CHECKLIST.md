# Restaurant POS Debug Checklist

## Problem: Table and item clicks not working

### Possible Causes (in order of likelihood):

1. **JavaScript not executing** - Check browser console for errors
2. **Elements not found** - `pos-floor` or buttons don't exist in DOM
3. **Event listeners not attaching** - Script runs before DOM ready
4. **CSS pointer-events** - Something blocking clicks
5. **Z-index issue** - Overlay blocking clicks

### Debug Steps:

**Open Browser Console (F12) and run:**

```javascript
// Check if elements exist
console.log('pos-floor exists:', document.getElementById('pos-floor'));
console.log('Tables:', document.querySelectorAll('.table-btn').length);
console.log('Items:', document.querySelectorAll('.add-item-btn').length);

// Check if event listeners are attached
console.log('currentTableId:', typeof currentTableId);
```

### What to look for:

- **Errors in console** (red text)
- **pos-floor: null** (element not found)
- **0 tables** (not rendering)
- **0 items** (not rendering)

### Most Likely Issue:

Based on the code structure, the issue is probably:

**The `DOMContentLoaded` wrapper is closing too early or there's a syntax error preventing the script from running.**

Check console for:
- `Uncaught SyntaxError`
- `Uncaught ReferenceError`
- `Cannot read property 'addEventListener' of null`
