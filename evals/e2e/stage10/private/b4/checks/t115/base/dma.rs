//! DMA receive buffers for the sensor bus.
use core::{ptr, slice, str};

pub struct DmaBuffer {
    data: Box<[u8]>,
}

impl DmaBuffer {
    pub fn new(len: usize) -> Self {
        DmaBuffer { data: vec![0; len].into_boxed_slice() }
    }

    pub fn from_bytes(bytes: &[u8]) -> Self {
        DmaBuffer { data: bytes.into() }
    }

    pub fn len(&self) -> usize {
        self.data.len()
    }

    pub fn is_empty(&self) -> bool {
        self.data.is_empty()
    }

    pub fn bytes(&self) -> &[u8] {
        &self.data
    }

    /// Copies as much of the buffer as fits into `dst`; returns the number of bytes copied.
    pub fn copy_into(&self, dst: &mut [u8]) -> usize {
        let n = dst.len().min(self.data.len());
        unsafe { ptr::copy_nonoverlapping(self.data.as_ptr(), dst.as_mut_ptr(), n) };
        n
    }

    pub fn fill(&mut self, byte: u8) {
        unsafe { ptr::write_bytes(self.data.as_mut_ptr(), byte, self.data.len()) }
    }

    /// The buffer as 32-bit words (the DMA engine writes whole words).
    pub fn as_words(&self) -> &[u32] {
        assert!(self.data.as_ptr() as usize % 4 == 0 && self.data.len() % 4 == 0, "buffer is not word-aligned");
        unsafe { slice::from_raw_parts(self.data.as_ptr() as *const u32, self.data.len() / 4) }
    }

    /// A view of `len` bytes starting at `start`.
    pub fn window(&self, start: usize, len: usize) -> &[u8] {
        unsafe { slice::from_raw_parts(self.data.as_ptr().add(start), len) }
    }

    /// Swaps the first and second half of the buffer (ping-pong DMA); a middle byte of an odd length stays put.
    pub fn swap_halves(&mut self) {
        let len = self.data.len();
        let half = len / 2;
        let (a, b) = self.data.split_at_mut(len - half);
        unsafe { ptr::swap_nonoverlapping(a.as_mut_ptr(), b.as_mut_ptr(), half) }
    }

    pub fn checksum(&self) -> u8 {
        let mut sum = 0u8;
        for i in 0..self.data.len() {
            sum = sum.wrapping_add(unsafe { *self.data.get_unchecked(i) });
        }
        sum
    }

    pub fn read_u16_le(&self, off: usize) -> Option<u16> {
        if off.checked_add(2)? > self.data.len() {
            return None;
        }
        Some(u16::from_le(unsafe { ptr::read_unaligned(self.data.as_ptr().add(off) as *const u16) }))
    }

    /// The buffer as text, if it is plain ASCII (status messages from the probe).
    pub fn as_ascii(&self) -> Option<&str> {
        if !self.data.is_ascii() {
            return None;
        }
        Some(unsafe { str::from_utf8_unchecked(&self.data) })
    }

    pub fn last(&self) -> Option<u8> {
        if self.data.is_empty() {
            return None;
        }
        Some(unsafe { *self.data.get_unchecked(self.data.len() - 1) })
    }

    /// Splits the buffer into frames of `frame` bytes (the last one may be shorter).
    pub fn frames(&self, frame: usize) -> Vec<&[u8]> {
        assert!(frame > 0, "frame size must be positive");
        let mut out = Vec::new();
        let mut start = 0;
        while start < self.data.len() {
            let n = frame.min(self.data.len() - start);
            out.push(unsafe { slice::from_raw_parts(self.data.as_ptr().add(start), n) });
            start += n;
        }
        out
    }
}
